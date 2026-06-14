---
name: payment-qr
description: Génère un QR code de paiement SEPA (EPC069-12) scannable par les apps bancaires FR/EU pour pré-remplir un virement (bénéficiaire, IBAN, montant, libellé). À utiliser dès qu'on demande un « QR de paiement / de virement », « un QR pour que X me paie N € », ou tout virement SEPA en euros. Pas pour PayPal/Lydia/carte.
---

# payment-qr — QR code de paiement SEPA (EPC)

Génère un **QR code de paiement EPC069-12** (SEPA Credit Transfer). Une fois
scanné par une app bancaire FR/EU, il pré-remplit le virement : bénéficiaire,
IBAN, montant, libellé. L'utilisateur n'a plus qu'à valider.

## Quand l'utiliser

- « génère-moi un QR de paiement / de virement »
- « un QR pour que X me paie 100 € »
- Tout virement **SEPA en euros**. (Pas pour PayPal/Lydia/carte — autre mécanisme.)

## Champs nécessaires

| Champ | Obligatoire | Note |
|---|---|---|
| Bénéficiaire (`--name`) | oui | celui qui **reçoit** l'argent, max 70 car. |
| IBAN (`--iban`) | oui | espaces tolérés, validé par regex |
| Montant (`--amount`) | non | EUR, ex. `100` ou `100,50`. Omis = montant libre |
| Libellé (`--label`) | non | référence, max 140 car. |
| BIC (`--bic`) | non | optionnel en EPC v002 |

## Procédure

1. Réunir au minimum **bénéficiaire + IBAN** (+ montant/libellé si connus). Si
   l'IBAN manque, le demander à l'utilisateur.
2. Lancer le script (Python 3, aucune dépendance binaire). Il réutilise un
   moteur QR déjà présent (`segno`, sinon `qrcode`+Pillow) ; sinon il installe
   `segno` via pip en s'adaptant au sandbox (PEP 668, site-packages verrouillé →
   venv isolé). Marche tel quel sous Claude.ai, en CI, ou sur un Mac Homebrew :
   ```bash
   python scripts/epc_qr.py --name "Carole Huet" \
     --iban "FR76 3000 4000 0312 3456 7890 143" \
     --amount 100 --label "Garde enfants juin 2026"
   ```
   Le script imprime un JSON (chemin du PNG + récap) sur stdout, et le payload
   EPC sur stderr. Le PNG est écrit dans le dossier courant par défaut, ou à
   `--out <chemin.png>`.
3. **Présenter le PNG** à l'utilisateur et **confirmer bénéficiaire + montant en
   clair** : il doit pouvoir vérifier avant d'envoyer l'argent.

## Bénéficiaires récurrents (registre, optionnel)

Pour générer un virement récurrent en une commande, créer un fichier
`beneficiaries.json` (chemin par défaut : dossier courant, ou variable
d'environnement `PAYMENT_QR_REGISTRY`, ou `--registry <chemin>`) :

```json
{
  "carole": { "name": "Carole Huet", "iban": "FR76...", "label": "Garde enfants" }
}
```

Puis :
```bash
python scripts/epc_qr.py --to carole --amount 100 --label "Garde juin 2026"
python scripts/epc_qr.py --list   # voir les bénéficiaires connus
```

La clé de registre (`carole`) est insensible à la casse. Les `--name/--iban/--label`
explicites priment sur le registre.

⚠️ **Un IBAN est une donnée sensible** : ne jamais committer ni logger
`beneficiaries.json`. Le garder hors d'un dépôt versionné.

## Garde-fous

- **Vérifier le bénéficiaire et le montant avec l'utilisateur** avant de
  présenter le QR — un IBAN erroné = argent envoyé au mauvais compte.
- EPC = euros SEPA uniquement. Montant entre 0,01 et 999 999 999,99 €.
  Payload ≤ 331 octets (sinon le script échoue proprement).
- Correction d'erreur **M**, marge 2, scale 8 → QR robuste au scan écran/print.

## Format technique (EPC069-12, version 002)

```
BCD            ← Service Tag
002            ← Version
1              ← Charset (1 = UTF-8)
SCT            ← SEPA Credit Transfer
<BIC>          ← optionnel
<Bénéficiaire>
<IBAN>
EUR<montant>   ← ex. EUR100.00, optionnel
<purpose>      ← optionnel, 4 car.
<ref structurée>
<libellé libre>
```
Lignes vides de fin tronquées. Encodage UTF-8.
