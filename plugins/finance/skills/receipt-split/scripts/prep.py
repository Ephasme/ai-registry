#!/usr/bin/env python3
"""Prepare a receipt photo for OCR: decode HEIC, honor EXIF, orient, and compress.

Two things wreck a vision model's read of a phone receipt photo:

1. Orientation. Phone photos are frequently rotated 90° (a long thermal strip held
   sideways), which mangles digit reading. This produces an upright JPG.
2. Size. A raw phone shot is 12+ megapixels and several MB. That whole image is base64'd
   into the extraction subagent's context — expensive — and Claude's vision pipeline
   downsamples anything past ~1568px on the long edge anyway, so the extra pixels buy no
   legibility, only tokens. So this also downscales (longest edge → --max-dim) and
   re-encodes as JPEG at --quality. Defaults are tuned for thermal receipts; the caller
   can override per receipt (see below).

Usage:
    python prep.py <input> [--out PATH] [--rotate auto|cw|ccw|0|90|180|270] [--all]
                   [--outdir DIR] [--max-dim N] [--quality Q]

    <input>          .heic/.heif/.jpg/.jpeg/.png (HEIC is converted automatically)
    --rotate auto    (default) if the image is landscape (wider than tall), rotate it 90°
                     clockwise so the receipt strip stands upright. This fixes the common
                     sideways case. It does NOT fix a 180° upside-down image — there's no
                     way to know up-from-down without reading the text, so if the extractor
                     reports the receipt is upside down, re-call with `--rotate 180`.
    --rotate N       apply an explicit clockwise rotation (cw=90, ccw=270).
    --all            write all four rotations (…_r0/_r90/_r180/_r270.jpg) and list them,
                     so the extractor can pick the legible orientation itself.
    --max-dim N      cap the longest edge at N pixels (default 1568, Claude's vision
                     long-edge limit — going higher only adds bytes, not detail the model
                     can see). Drop it lower (e.g. 1200) for a short, large-print ticket to
                     save more; 0 disables downscaling. If a dense, small-print receipt
                     fails its cross-check on misread digits, re-prep nearer 1568 (and bump
                     --quality) before blaming the OCR.
    --quality Q      JPEG quality 1–100 (default 80). Thermal print is high-contrast
                     black-on-white, so 80 stays legible while shrinking the file a lot;
                     raise toward 90 only if fine print smears.

Degrees are CLOCKWISE. Prints a JSON line: input, output(s), rotation_applied, size,
orientation, and bytes (final file size) so you can confirm the compression took. If
neither Pillow nor macOS sips is available, it exits with the exact install command rather
than producing a giant uncompressed image — relay that to the user.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROT = {"0": 0, "90": 90, "180": 180, "270": 270, "cw": 90, "ccw": 270, "auto": "auto"}
MAX_DIM_DEFAULT = 1568  # Claude downsamples the long edge to this; larger is wasted bytes
QUALITY_DEFAULT = 80


def _load_pillow():
    try:
        from PIL import Image, ImageOps  # noqa
        return Image, ImageOps
    except ImportError:
        return None, None


def _have_sips():
    return sys.platform == "darwin" and shutil.which("sips") is not None


def _heic_to_jpg_sips(src):
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    subprocess.run(["sips", "-s", "format", "jpeg", src, "--out", tmp],
                   check=True, capture_output=True)
    return tmp


def _save_rotation_sips(src, degrees, out, max_dim, quality):
    shutil.copyfile(src, out)
    cmd = ["sips"]
    if degrees:
        cmd += ["-r", str(degrees)]
    if max_dim:
        cmd += ["-Z", str(max_dim)]  # resample so the LONGEST edge is at most max_dim
    cmd += ["-s", "format", "jpeg", "-s", "formatOptions", str(quality), out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: python prep.py <input> [--out PATH] [--rotate auto|cw|ccw|0|90|180|270] [--all] [--outdir DIR] [--max-dim N] [--quality Q]")
    src = args[0]
    if not os.path.isfile(src):
        sys.exit(f"no such file: {src}")

    out = None
    outdir = None
    rotate = "auto"
    emit_all = False
    max_dim = MAX_DIM_DEFAULT
    quality = QUALITY_DEFAULT
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--out":
            i += 1; out = args[i]
        elif a == "--outdir":
            i += 1; outdir = args[i]
        elif a == "--rotate":
            i += 1; rotate = args[i]
            if rotate not in ROT:
                sys.exit(f"--rotate must be one of {', '.join(ROT)}")
        elif a == "--all":
            emit_all = True
        elif a == "--max-dim":
            i += 1
            try:
                max_dim = int(args[i])
            except ValueError:
                sys.exit("--max-dim must be an integer (pixels), 0 to disable")
            if max_dim < 0:
                sys.exit("--max-dim must be >= 0")
        elif a == "--quality":
            i += 1
            try:
                quality = int(args[i])
            except ValueError:
                sys.exit("--quality must be an integer 1-100")
            if not 1 <= quality <= 100:
                sys.exit("--quality must be between 1 and 100")
        else:
            sys.exit(f"unexpected argument: {a}")
        i += 1

    base = os.path.splitext(os.path.basename(src))[0]
    outdir = outdir or os.path.dirname(os.path.abspath(src))
    os.makedirs(outdir, exist_ok=True)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    is_heic = src.lower().endswith((".heic", ".heif"))

    Image, ImageOps = _load_pillow()

    # ---- Pillow path (cross-platform; sips used only to decode HEIC if pillow-heif absent)
    if Image is not None and ImageOps is not None:
        try:
            if is_heic:
                try:
                    import pillow_heif  # type: ignore
                    pillow_heif.register_heif_opener()
                    img = Image.open(src)
                except ImportError:
                    if not _have_sips():
                        sys.exit("HEIC needs pillow-heif (pip install pillow-heif) or macOS sips")
                    img = Image.open(_heic_to_jpg_sips(src))
            else:
                img = Image.open(src)
            img = ImageOps.exif_transpose(img).convert("RGB")
        except Exception as e:  # noqa
            sys.exit(f"could not open image: {e}")

        def save(im, path):
            # thumbnail caps the LONGEST edge at max_dim, preserves aspect, in place
            if max_dim and max(im.size) > max_dim:
                im.thumbnail((max_dim, max_dim), Image.LANCZOS)
            im.save(path, "JPEG", quality=quality, optimize=True)
            return im

        if emit_all:
            outs = {}
            for deg in (0, 90, 180, 270):
                p = os.path.join(outdir, f"{base}_r{deg}.jpg")
                saved = save(img.rotate(-deg, expand=True), p)  # PIL rotate is CCW; negative = CW
                outs[deg] = {"path": p, "size": list(saved.size), "bytes": os.path.getsize(p)}
            print(json.dumps({"input": src, "outputs": outs,
                              "max_dim": max_dim, "quality": quality}))
            return

        if rotate == "auto":
            w, h = img.size
            degrees = 90 if w > h else 0
        else:
            degrees = ROT[rotate]
        result = img.rotate(-degrees, expand=True) if degrees else img
        out = out or os.path.join(outdir, f"{base}_upright.jpg")
        result = save(result, out)
        print(json.dumps({"input": src, "output": out, "rotation_applied": degrees,
                          "size": list(result.size),
                          "orientation": "portrait" if result.size[1] >= result.size[0] else "landscape",
                          "max_dim": max_dim, "quality": quality,
                          "bytes": os.path.getsize(out)}))
        return

    # ---- sips-only fallback (macOS, no Python imaging libs)
    if not _have_sips():
        sys.exit("need either Pillow (pip install Pillow) or macOS sips to process images")
    work = _heic_to_jpg_sips(src) if is_heic else src

    if emit_all:
        outs = {}
        for deg in (0, 90, 180, 270):
            p = os.path.join(outdir, f"{base}_r{deg}.jpg")
            _save_rotation_sips(work, deg, p, max_dim, quality)
            outs[deg] = {"path": p, "bytes": os.path.getsize(p)}
        print(json.dumps({"input": src, "outputs": outs,
                          "max_dim": max_dim, "quality": quality}))
        return

    if rotate == "auto":
        dims = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", work],
                              check=True, capture_output=True, text=True).stdout
        nums = [int(t.split(":")[1]) for t in dims.splitlines() if ":" in t]
        w, h = (nums + [0, 0])[:2]
        degrees = 90 if w > h else 0
    else:
        degrees = ROT[rotate]
    out = out or os.path.join(outdir, f"{base}_upright.jpg")
    _save_rotation_sips(work, degrees, out, max_dim, quality)
    print(json.dumps({"input": src, "output": out, "rotation_applied": degrees,
                      "max_dim": max_dim, "quality": quality,
                      "bytes": os.path.getsize(out)}))


if __name__ == "__main__":
    main()
