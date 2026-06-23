# Reading French receipts (ticket de caisse + facturette CB)

Reference for extracting expense data from French retail receipts. Load this when a
receipt is unusual, the total fails its cross-check, or you need to disambiguate a
payment-card number from a loyalty-card number. Receipts here are **always French**.

A French purchase usually prints two blocks on one thermal strip: the **ticket de caisse**
(itemized store receipt) and below it the **ticket carte bancaire / facturette** (the
card-terminal slip). Read the final amount from the totals block and corroborate it
against the facturette.

## 1. Which line is the amount paid

`TTC` = *Toutes Taxes Comprises* (tax-included) — always the figure to charge.
`HT` = *Hors Taxes* (pre-tax) — never use it.

**Use** (final amount), rough priority:
- `NET A PAYER` / `RESTE A PAYER` — the most explicit "what the customer pays" (after discounts/rounding); prefer when present.
- `TOTAL TTC` / `TOTAL` / `TOTAL HORS AVANTAGES`
- `MONTANT DU` / `MONTANT DÛ`, `A PAYER`, `MONTANT`
- On the facturette: `MONTANT` — the charged amount, used for the cross-check (§6).

**Ignore** (never the amount):
- `HT`, `TOTAL HT`, `Hors Taxes`; `TVA`, `DONT TVA`, `TVA 5,5/10/20%`, `TOTAL TVA`
- `SOUS-TOTAL`; per-article prices, quantities, `PRIX/KG`, `x2`
- Loyalty balances: `CAGNOTTE`, `AVANTAGE FIDELITE`, `SOLDE FIDELITE`, points/euros earned
- `RENDU` / `MONNAIE` (change given), `ESPECES`/cash tendered, `ARRONDI` (rounding — already folded into `NET A PAYER`)

Several `TOTAL` lines can appear (one per VAT rate). The real one is labeled `TTC` /
`NET A PAYER`, usually the largest and in a bold/double-height font.

## 2. Number format

- **Decimal is a comma**: `23,94` = 23.94. A dot is a thousands separator (`1.234,50`) or OCR noise — never the decimal point. Normalize output to dot-decimal (`23.94`).
- **Euro** trails the amount: `23,94 €`, `23,94€`, `EUR 23,94`, `23,94 EUR`.
- **Thermal-OCR digit confusions** to watch: `0↔O↔D`, `1↔I↔l↔7`, `8↔B`, `5↔S`, `6↔G`, `2↔Z↔3`, `9↔g`, `4↔A`, plus `,↔.` and `€↔E/C`. Faded/cut print drops or doubles digits — the §6 cross-check is the main defense.

## 3. The card slip (facturette) — where the CB last-4 lives

Fields, roughly top to bottom:
- **Scheme/app**: `CB`, `CARTE BANCAIRE`, `CB CONTACT`, `VISA`, `MASTERCARD`, `DEBIT MASTERCARD`.
- **Type**: `DEBIT` (purchase) or `CREDIT` (refund). `DEBIT` confirms a charge.
- **AID (EMV Application Identifier)** — a hex string like `A0000000031010`. **NOT the card number.** Identifies the network: `A0000000031010` = Visa, `A0000000041010` = Mastercard, `A0000000421010` = CB (France). Always ~14–16 hex chars starting `A000000003/04/042…`. Label it AID and discard for amount/card purposes.
- **Masked PAN (the card number)** — only the **last 4 digits** are real. Renderings: `XXXXXXXXXXXX1234`, `XXXX XXXX XXXX 1234`, `############1234`, `**** **** **** 1234`, `No ....1234`, `No: ............1234`. Keep the trailing 4. (Since ~2001 the full PAN is not printed on the customer copy — and some receipts print no PAN at all, only the EMV confirmation.)
- **MONTANT** — the charged amount (= receipt total; §6).
- **Contactless**: `SANS CONTACT`, `CONTACTLESS`, `CB CONTACT`, `NFC`.
- **Ignore** for extraction: `No AUTO`/`AUTORISATION` (auth code), `No transaction`, `CONTRAT`, terminal/`TPE`/`MID` ids, `cryptogramme`/`ARQC` hex.

**Card last-4 vs loyalty card — do not confuse.** The payment last-4 sits **inside the
facturette** next to `CB`/`CARTE BANCAIRE`/`DEBIT`/AID/`MONTANT`, as a *masked* number.
A loyalty number sits under a different heading — `CARTE FIDELITE`, `COMPTE FIDELITE`,
`CARTE M'` (Monoprix), `CARTE PASS` (Carrefour), `N° ADHERENT` — printed *in full* (10–16+
digits in clear), tied to points/euros, with no AID and no masking. Rule: masked + EMV
context → payment card; fully-printed + `FIDELITE`/`ADHERENT` → loyalty, **never** use it.

If no masked payment PAN is printed (common — e.g. Monoprix often prints only the EMV
confirmation), `card_last4` is **null**. Do not substitute the loyalty number.

## 4. Payment method (card vs cash)

- **Card**: a facturette block, or any of `CARTE BANCAIRE`, `CB`, `CARTE`, `VISA`/`MASTERCARD`, `DEBIT`, an AID, a masked PAN, `No AUTO`. → `card`.
- **Cash**: `ESPECES` (`ESP`), usually with `RECU`/`REÇU` (tendered) and `RENDU`/`MONNAIE` (change). `RENDU`/`MONNAIE` present and no facturette ≈ cash. → `cash`. No card last-4 exists.
- Others: `CHEQUE`, `TICKET RESTAURANT`/`TR`/`CONECS`, `ANCV`. Split payments can show both.
- Note: a `Rendu 0,00€` line can appear even on a card payment — it's not by itself proof of cash.

## 5. Date / time

- `JJ/MM/AAAA` (`12/03/2024`) or `JJ/MM/AA` (`12/03/24`); also `JJ.MM.AAAA`, `JJ-MM-AAAA`. **Day-first** — never US `MM/DD`.
- Combined: `le 12/03/2024 à 14:35`, `12/03/24 14:35`. 24-hour time.
- If the header has no date, a loyalty "solde au JJ/MM/AA" line is a weak fallback — flag the uncertainty.

## 6. Cross-check (primary confidence signal)

The total appears **twice**: in the totals block (`TOTAL TTC` / `NET A PAYER`) and on the
facturette as `MONTANT`. Read both, normalize comma→dot, confirm they agree. A match is
strong confidence; a mismatch means OCR fumbled one of them — re-examine (rotating the
image upright often fixes it) rather than silently picking one.

## Sources

- DGCCRF / economie.gouv.fr — Ticket de caisse et de carte bancaire: https://www.economie.gouv.fr/dgccrf/les-fiches-pratiques/ticket-de-caisse-et-de-carte-bancaire
- Legalstart — mentions obligatoires (HT/TVA/TTC): https://www.legalstart.fr/fiches-pratiques/facturation/ticket-caisse-mention-obligatoire/
- Web-monétique — savoir lire un ticket carte bancaire (PAN tronqué, EMV, cryptogramme): https://www.web-monetique.fr/astuces-et-conseils/ticket-carte-bancaire/
- Crédit-et-Banque — zones d'un ticket CB / codes AID (A0000000031010 = Visa, …041010 = MC, …421010 = CB): https://www.credit-et-banque.com/lire-un-ticket-de-carte-bancaire/ · https://www.credit-et-banque.com/liste-des-codes-aid/
- EFTLab — complete list of EMV AIDs: https://www.eftlab.com/knowledge-base/complete-list-of-application-identifiers-aid
