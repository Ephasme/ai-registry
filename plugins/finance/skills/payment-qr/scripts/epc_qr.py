#!/usr/bin/env python3
"""
epc_qr.py — Génère un QR code de paiement EPC069-12 (SEPA Credit Transfer).

Scannable par la quasi-totalité des apps bancaires FR/EU : pré-remplit un
virement (bénéficiaire, IBAN, montant, libellé). L'utilisateur n'a plus qu'à
valider dans son app.

Pur Python : utilise `segno` (PNG natif, aucune dépendance binaire). Si le
module est absent, le script tente `pip install segno` automatiquement.

Exemples :
  python scripts/epc_qr.py --name "Carole Huet" --iban "FR76 3000 4000 0312 3456 7890 143" \
      --amount 100 --label "Garde enfants juin 2026"
  python scripts/epc_qr.py --to carole --amount 100 --label "Garde juin"
  python scripts/epc_qr.py --list
"""
import argparse
import json
import os
import re
import subprocess
import sys


def render_qr(payload, out_path):
    """Écrit le QR (PNG) avec segno si dispo, sinon qrcode, sinon pip install segno.

    Niveau de correction M, marge 2, scale 8 → robuste au scan écran/print.
    """
    # 1) segno (pur Python, PNG natif) si déjà présent
    try:
        import segno
        segno.make(payload, error="m").save(out_path, scale=8, border=2)
        return "segno"
    except ModuleNotFoundError:
        pass

    # 2) qrcode (souvent présent dans les sandboxes) en fallback
    try:
        import qrcode
        qrcode.make(
            payload,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        ).save(out_path)
        return "qrcode"
    except ModuleNotFoundError:
        pass

    # 3) dernier recours : installer segno via pip
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "segno"],
            check=True,
        )
        import segno
        segno.make(payload, error="m").save(out_path, scale=8, border=2)
        return "segno"
    except Exception:
        sys.stderr.write(
            '❌ aucune lib QR disponible (segno/qrcode) et installation impossible.\n'
            "   Installe-en une : pip install segno\n"
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
