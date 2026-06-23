#!/usr/bin/env python3
"""Prepare a receipt photo for OCR: decode HEIC, honor EXIF, and set orientation.

Phone receipt photos are frequently rotated 90° (a long thermal strip held sideways),
which wrecks a vision model's digit reading. This produces an upright JPG.

Usage:
    python orient.py <input> [--out PATH] [--rotate auto|cw|ccw|0|90|180|270] [--all] [--outdir DIR]

    <input>          .heic/.heif/.jpg/.jpeg/.png (HEIC is converted automatically)
    --rotate auto    (default) if the image is landscape (wider than tall), rotate it 90°
                     clockwise so the receipt strip stands upright. This fixes the common
                     sideways case. It does NOT fix a 180° upside-down image — there's no
                     way to know up-from-down without reading the text, so if the extractor
                     reports the receipt is upside down, re-call with `--rotate 180`.
    --rotate N       apply an explicit clockwise rotation (cw=90, ccw=270).
    --all            write all four rotations (…_r0/_r90/_r180/_r270.jpg) and list them,
                     so the extractor can pick the legible orientation itself.

Degrees are CLOCKWISE. Prints a JSON line: input, output(s), rotation_applied, size,
orientation. On success the prepared image is what you feed to the extraction subagent.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROT = {"0": 0, "90": 90, "180": 180, "270": 270, "cw": 90, "ccw": 270, "auto": "auto"}


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


def _save_rotation_sips(src, degrees, out):
    shutil.copyfile(src, out)
    if degrees:
        subprocess.run(["sips", "-r", str(degrees), out], check=True, capture_output=True)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: python orient.py <input> [--out PATH] [--rotate auto|cw|ccw|0|90|180|270] [--all] [--outdir DIR]")
    src = args[0]
    if not os.path.isfile(src):
        sys.exit(f"no such file: {src}")

    out = None
    outdir = None
    rotate = "auto"
    emit_all = False
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
            im.save(path, "JPEG", quality=92)

        if emit_all:
            outs = {}
            for deg in (0, 90, 180, 270):
                p = os.path.join(outdir, f"{base}_r{deg}.jpg")
                save(img.rotate(-deg, expand=True), p)  # PIL rotate is CCW; negative = CW
                outs[deg] = p
            print(json.dumps({"input": src, "outputs": outs, "size": list(img.size)}))
            return

        if rotate == "auto":
            w, h = img.size
            degrees = 90 if w > h else 0
        else:
            degrees = ROT[rotate]
        result = img.rotate(-degrees, expand=True) if degrees else img
        out = out or os.path.join(outdir, f"{base}_upright.jpg")
        save(result, out)
        print(json.dumps({"input": src, "output": out, "rotation_applied": degrees,
                          "size": list(result.size),
                          "orientation": "portrait" if result.size[1] >= result.size[0] else "landscape"}))
        return

    # ---- sips-only fallback (macOS, no Python imaging libs)
    if not _have_sips():
        sys.exit("need either Pillow (pip install Pillow) or macOS sips to process images")
    work = _heic_to_jpg_sips(src) if is_heic else src

    if emit_all:
        outs = {}
        for deg in (0, 90, 180, 270):
            p = os.path.join(outdir, f"{base}_r{deg}.jpg")
            _save_rotation_sips(work, deg, p)
            outs[deg] = p
        print(json.dumps({"input": src, "outputs": outs}))
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
    _save_rotation_sips(work, degrees, out)
    print(json.dumps({"input": src, "output": out, "rotation_applied": degrees}))


if __name__ == "__main__":
    main()
