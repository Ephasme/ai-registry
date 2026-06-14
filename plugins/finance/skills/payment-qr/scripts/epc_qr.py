#!/usr/bin/env python3
"""
epc_qr.py — Génère un QR code de paiement EPC069-12 (SEPA Credit Transfer).

Scannable par la quasi-totalité des apps bancaires FR/EU : pré-remplit un
virement (bénéficiaire, IBAN, montant, libellé). L'utilisateur n'a plus qu'à
valider dans son app.

Pur Python, aucune dépendance binaire. Cherche un moteur QR déjà présent
(`segno`, puis `qrcode`+Pillow) ; sinon installe `segno` via pip en s'adaptant
au sandbox (PEP 668, site-packages verrouillé → venv isolé). Marche tel quel
dans le sandbox Claude.ai, en CI, ou sur un Mac Homebrew.

Exemples :
  python scripts/epc_qr.py --name "Carole Huet" --iban "FR76 3000 4000 0312 3456 7890 143" \
      --amount 100 --label "Garde enfants juin 2026"
  python scripts/epc_qr.py --to carole --amount 100 --label "Garde juin"
  python scripts/epc_qr.py --list
"""
import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile


def _save_segno(payload, out_path):
    import segno
    segno.make(payload, error="m").save(out_path, scale=8, border=2)


def _save_qrcode(payload, out_path):
    import qrcode
    qrcode.make(
        payload,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    ).save(out_path)


def _try_save(saver, payload, out_path):
    """Tente un moteur déjà importable. True si le PNG est écrit.

    ModuleNotFoundError / ImportError = lib (ou sa dépendance, ex. Pillow pour
    qrcode) absente → moteur suivant. Toute autre erreur (payload, disque…) remonte.
    """
    try:
        saver(payload, out_path)
        return True
    except (ModuleNotFoundError, ImportError):
        return False


def _pip_install_segno(python, *flags):
    """`python -m pip install segno` silencieux. True si le code retour est 0."""
    try:
        r = subprocess.run(
            [python, "-m", "pip", "install", "--quiet", *flags, "segno"],
            capture_output=True, text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


def render_qr(payload, out_path):
    """Écrit le QR (PNG). Correction M, marge 2, scale 8 → robuste au scan.

    Ordre du moins au plus coûteux, pour marcher dans un sandbox sans rien
    supposer de préinstallé ni de la politique pip :
      1. segno puis qrcode s'ils sont déjà là (aucun réseau) ;
      2. pip install segno dans l'interpréteur courant, en enchaînant les jeux
         d'options qui survivent à PEP 668 et à un site-packages utilisateur ;
      3. dernier recours : un venv isolé jetable (env courant non inscriptible
         mais réseau dispo — cas du sandbox Claude.ai durci).
    """
    # 1) moteur déjà présent — zéro réseau
    for saver, name in ((_save_segno, "segno"), (_save_qrcode, "qrcode")):
        if _try_save(saver, payload, out_path):
            return name

    # 2) installer segno dans l'interpréteur courant : défaut → --user →
    #    --break-system-packages (PEP 668) → les deux.
    for flags in ([], ["--user"], ["--break-system-packages"],
                  ["--user", "--break-system-packages"]):
        if _pip_install_segno(sys.executable, *flags):
            importlib.invalidate_caches()
            if _try_save(_save_segno, payload, out_path):
                return "segno (pip {})".format(" ".join(flags) or "défaut")

    # 3) venv isolé jetable : site-packages courant verrouillé mais réseau OK.
    try:
        import venv
        vdir = tempfile.mkdtemp(prefix="payment-qr-venv-")
        venv.create(vdir, with_pip=True)
        bindir = "Scripts" if os.name == "nt" else "bin"
        vpy = os.path.join(vdir, bindir, "python.exe" if os.name == "nt" else "python")
        if _pip_install_segno(vpy):
            payload_file = os.path.join(vdir, "payload.txt")
            with open(payload_file, "w", encoding="utf-8") as f:
                f.write(payload)
            child = (
                "import segno,sys;"
                "p=open(sys.argv[1],encoding='utf-8').read();"
                "segno.make(p,error='m').save(sys.argv[2],scale=8,border=2)"
            )
            r = subprocess.run([vpy, "-c", child, payload_file, out_path],
                               capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(out_path):
                return "segno (venv isolé)"
    except Exception:
        pass

    # 4) abandon — message actionnable
    sys.stderr.write(
        "❌ Aucun moteur QR disponible et installation impossible.\n"
        "   segno/qrcode absents, et pip a échoué (pas de réseau ou env verrouillé).\n"
        "   Installe-en un manuellement : pip install segno   (ou : pip install qrcode pillow)\n"
    )
    sys.exit(3)


def registry_path(explicit=None):
    if explicit:
        return os.path.abspath(explicit)
    return os.path.abspath(
        os.environ.get("PAYMENT_QR_REGISTRY", "beneficiaries.json")
    )


def load_registry(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_epc_payload(name, iban, amount=None, bic="", label="", purpose=""):
    if not name:
        raise ValueError("bénéficiaire (--name) requis")
    if not iban:
        raise ValueError("IBAN (--iban) requis")

    iban_clean = re.sub(r"\s+", "", str(iban)).upper()
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$", iban_clean):
        raise ValueError("IBAN invalide : " + str(iban))

    amt_line = ""
    if amount not in (None, "", True):
        try:
            n = float(str(amount).replace(",", "."))
        except ValueError:
            raise ValueError("montant invalide : " + str(amount))
        if not (0.01 <= n <= 999999999.99):
            raise ValueError("montant hors limites EPC : " + str(amount))
        amt_line = "EUR{:.2f}".format(n)

    lines = [
        "BCD", "002", "1", "SCT",
        re.sub(r"\s+", "", str(bic or "")).upper(),
        str(name)[:70],
        iban_clean,
        amt_line,
        str(purpose or "")[:4],
        "",
        str(label or "")[:140],
    ]
    while lines and lines[-1] == "":
        lines.pop()

    payload = "\n".join(lines)
    nbytes = len(payload.encode("utf-8"))
    if nbytes > 331:
        raise ValueError("payload {} octets > 331 (limite EPC)".format(nbytes))
    return payload, nbytes


def main():
    p = argparse.ArgumentParser(
        description="Génère un QR de paiement SEPA (EPC069-12)."
    )
    p.add_argument("--name", help="bénéficiaire (celui qui reçoit), max 70 car.")
    p.add_argument("--iban", help="IBAN du bénéficiaire (espaces tolérés)")
    p.add_argument("--amount", help="montant EUR, ex. 100 ou 100,50 (optionnel)")
    p.add_argument("--label", help="libellé / référence, max 140 car. (optionnel)")
    p.add_argument("--bic", help="BIC (optionnel en EPC v002)")
    p.add_argument("--purpose", help="purpose code, 4 car. (optionnel)")
    p.add_argument("--out", help="chemin du PNG de sortie")
    p.add_argument("--to", help="clé d'un bénéficiaire enregistré (registre)")
    p.add_argument("--registry", help="chemin du registre JSON des bénéficiaires")
    p.add_argument("--list", action="store_true", help="liste les bénéficiaires connus")
    args = p.parse_args()

    reg_path = registry_path(args.registry)
    registry = load_registry(reg_path)

    if args.list:
        if not registry:
            print("Aucun bénéficiaire enregistré ({}).".format(reg_path))
            return
        print("Bénéficiaires enregistrés :")
        for k, v in registry.items():
            print("  - {} → {} ({})".format(k, v.get("name"), v.get("iban")))
        return

    name, iban = args.name, args.iban
    bic, label = args.bic, args.label

    if args.to:
        b = registry.get(str(args.to).lower())
        if not b:
            raise SystemExit(
                '❌ bénéficiaire "{}" inconnu. --list pour voir les dispos.'.format(args.to)
            )
        name = name or b.get("name")
        iban = iban or b.get("iban")
        bic = bic or b.get("bic")
        label = label or b.get("label")

    payload, nbytes = build_epc_payload(
        name, iban, args.amount, bic, label, args.purpose
    )

    safe = re.sub(r"[^a-z0-9]+", "_", str(name), flags=re.I).lower()
    out_path = (
        os.path.abspath(args.out)
        if args.out
        else os.path.join(os.getcwd(), "epc-{}-{}.png".format(safe, args.amount or "libre"))
    )

    engine = render_qr(payload, out_path)

    print(json.dumps({
        "engine": engine,
        "ok": True,
        "out": out_path,
        "bytes": nbytes,
        "beneficiaire": name,
        "iban": re.sub(r"\s+", "", str(iban)).upper(),
        "montant": (
            "{:.2f} EUR".format(float(str(args.amount).replace(",", ".")))
            if args.amount else "(libre)"
        ),
        "libelle": label or "",
    }, ensure_ascii=False, indent=2))
    sys.stderr.write("\nPayload EPC :\n" + payload + "\n")


if __name__ == "__main__":
    # ValueError -> message convivial + exit 1.
    # SystemExit (install segno KO, bénéficiaire inconnu) garde son code/msg.
    try:
        main()
    except ValueError as e:
        sys.stderr.write("❌ " + str(e) + "\n")
        sys.exit(1)
