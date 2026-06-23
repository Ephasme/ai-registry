---
name: receipt-split
description: Extract expense data from one or more French receipt photos and post each to Splitwise, split 50/50 between Loup (you) and Cassandra. Use whenever receipt or ticket photos are shared — a single photo, several, or a folder — and the user wants them on Splitwise (phrasings like add this receipt to Splitwise, split these tickets with Cassandra, ajoute ces reçus sur Splitwise, note this purchase to share), or asks to expense or split a bill — even if they don't say Splitwise out loud. Who paid is read from the CB card last-4 or the loyalty/fidélité account printed on the receipt (you keep a local identity registry); it asks when neither resolves, and always shows a summary you approve before creating anything.
---

# receipt-split — French receipts → Splitwise, split 50/50

Turn one or many receipt photos into Splitwise expenses, each split 50/50 between
**Loup** (the current Splitwise user) and **Cassandra**. Receipts are **always French**
(*ticket de caisse* + *facturette carte bancaire*).

**Division of labour — two models, on purpose:**
- **Sonnet 4.6 subagents** do the OCR: one per photo, in parallel — fast, cheap, strong at
  messy thermal print. They export *everything* (line items, discounts, fees, totals,
  payment method, card last-4, loyalty block).
- **This orchestrating session (Opus 4.8)** does the *verification and the writes*:
  recompute the sum from the items and reconcile it against the printed total; if it
  doesn't add up, send the receipt back to Sonnet with specific comments and re-read.
  Cheap OCR, careful arithmetic — the numbers get checked, not trusted.

## When to use

- The user shares receipt/ticket photo(s) and wants them shared with Cassandra.
- "Add these to Splitwise", "split this bill", "ajoute ces tickets", "on partage ça".
- One photo, several, or a whole folder — same flow, fanned out.

Not for: generating a payment QR (use `payment-qr`) or reading bank transactions (`bank`).

## Prerequisites

- **Splitwise tools** reachable (`mcp__plugin_finance_splitwise__*`). If a call returns
  `SPLITWISE_API_KEY is not set` / auth errors, the server isn't configured — say so and
  stop; the writes can't happen.
- **Identity registry** — a local JSON mapping payment cards *and* loyalty accounts to a
  person, plus the two names. It holds personal data, so it lives **outside this public
  repo** and is never committed. Resolution order:
  1. `$RECEIPT_CARDS_REGISTRY`, else
  2. `$CLAUDE_CONFIG_DIR/receipt-cards.json` (e.g. `~/.claude-perso/receipt-cards.json`), else
  3. `~/.config/receipt-split/cards.json`.

  Format:
  ```json
  {
    "self": "Loup",
    "partner": "Cassandra",
    "cards": { "1234": "Loup", "5678": "Cassandra" },
    "loyalty": [
      { "person": "Cassandra", "merchant": "Monoprix",
        "client_name": "De Carvalho", "client_id_suffix": "042", "card_number": "4021573104" }
    ]
  }
  ```
  `self` is the current Splitwise user; `partner` is the other person. If the file is
  missing the skill still runs — it just can't auto-detect the payer and asks each time.
  When you newly identify a card or loyalty account, offer to append it so next time is
  automatic.

## Procedure

### 1. Prepare each photo (decode + orient + compress)

Run every input through the prep script — it decodes HEIC (default iPhone format), honours
EXIF, sets orientation, and **downscales + re-encodes** so the image is small *before* it
ever reaches a subagent:
```bash
python scripts/prep.py <input> --out /tmp/<name>_upright.jpg
```

**Why compress.** A raw phone shot is 12+ MP and several MB; that whole image gets base64'd
into the OCR subagent's context — expensive — and Claude's vision pipeline downsamples
anything past ~1568px on the long edge anyway, so the extra pixels cost tokens without
buying legibility. The script caps the long edge (`--max-dim`, default 1568) and re-encodes
as JPEG (`--quality`, default 80). The defaults suit a typical thermal receipt; **pick per
receipt** rather than treating them as fixed:
- short, large-print ticket → go smaller (`--max-dim 1000 --quality 70`) to save more.
- dense, small-print receipt → stay near 1568 with `--quality 90` so digits keep their
  edges; don't exceed 1568 (the model can't see past it). `--max-dim 0` disables downscaling.

The JSON it prints carries final `size` and `bytes` — glance at them to confirm the image
actually shrank. If step 3's cross-check later fails on *misread digits*, **re-prep
larger/sharper before** concluding the OCR erred — you may simply have compressed too hard.

**Orientation.** Phone receipts are often shot with the strip lying **sideways**, which
wrecks digit reading — and aspect-ratio alone can't detect it (a portrait photo can still
hold a sideways receipt). So treat orientation as something the **model** confirms: if
step 2's extractor reports the image is rotated/upside-down or its numbers fail the
cross-check (step 3), re-orient and re-extract:
```bash
python scripts/prep.py <input> --rotate 90    # or 270 / 180 (degrees clockwise)
python scripts/prep.py <input> --all          # emit r0/r90/r180/r270; let Sonnet pick the legible one
```

**Missing tooling.** The script needs Pillow (`pip install Pillow`) or macOS `sips`; for
HEIC without `sips` it also needs `pillow-heif` (`pip install pillow-heif`). If it exits
asking for one of these, relay the exact install command to the user and stop — do **not**
fall back to handing the raw multi-MB image to the subagent, since that's the context
blow-up this step exists to prevent.

PDFs are read directly. If you can't find any image, ask for the path rather than guessing.

### 2. Extract each receipt with a Sonnet 4.6 subagent

Dispatch **one subagent per photo in a single message** (parallel) via the Agent tool with
**`model: "sonnet"`**. For French-receipt specifics — which line is the amount paid
(`NET A PAYER`/`RESTE A PAYER`/`TOTAL TTC`, never `HT`), comma decimals, the facturette,
loyalty-vs-payment-card disambiguation — the detailed reference is
[`references/french-receipts.md`](references/french-receipts.md); point the subagent there
if a receipt is unusual. Give each subagent this prompt (substitute the path):

> Read the French receipt image at `<ABSOLUTE_PATH>` and export its data. Return **only**
> one JSON object, no prose:
> ```json
> {
>   "merchant": "store name, or null",
>   "date": "purchase date YYYY-MM-DD, or null",
>   "currency": "EUR",
>   "items":     [{"label": "line label", "amount": "line total, dot-decimal e.g. 3.05"}],
>   "discounts": [{"label": "e.g. AVANTAGE / coupon that REDUCES the amount paid", "amount": "1.00"}],
>   "fees":      [{"label": "e.g. consigne / sac / frais that ADDS to the amount", "amount": "0.10"}],
>   "subtotal_printed": "e.g. TOTAL HORS AVANTAGES, or null",
>   "total": "the amount actually paid — NET A PAYER / RESTE A PAYER / TOTAL TTC — dot-decimal",
>   "total_crosscheck": "the amount printed on the card slip (CB/facturette MONTANT/DEBIT), or null",
>   "tva_ttc": "the TTC figure from the TVA table, or null",
>   "payment_method": "card | cash | unknown",
>   "card_last4": "last 4 of the MASKED payment-card PAN on the facturette, or null",
>   "loyalty": {"client_name": "name greeted/printed, or null", "client_id": "loyalty/client number or its visible suffix, or null", "merchant_program": "e.g. Monoprix M', or null"}
> }
> ```
> Rules: amounts use a French comma (`23,94`) → output dot-decimal (`23.94`). Read the
> total DIGIT BY DIGIT (thermal print blurs 3/8, 2/3, 5/6, 0/8). The total usually prints
> 2–3 times (totals block, facturette `MONTANT`, TVA `TTC`) — they must agree; if they
> don't, report each value in a `"notes"` field. `card_last4` is the MASKED PAN only —
> never a loyalty/fidélité card number (`COMPTE/CARTE FIDELITE`) and never an EMV AID like
> `A0000000031010`. If the image is rotated or unreadable, say so in `"notes"` instead of
> guessing. Do not invent values.

### 3. Reconcile the numbers (orchestrator — don't trust, verify)

For each extracted receipt, **you** recompute and check before going further:

- `computed = Σ items − Σ discounts + Σ fees`
- It must equal `total` (to the cent). And `total` must equal `total_crosscheck` and
  `tva_ttc` when those are present — each is an independent print of the same number.

If everything agrees, the total is confident — proceed. **If anything is off**, send the
receipt **back to the same Sonnet subagent** (continue it with SendMessage, or dispatch a
fresh one) with a concrete comment, e.g.:

> Your line items sum to 23.91 but the printed total is 23.94, and the facturette MONTANT
> reads 23.94 — so an item amount is misread by ~0.03. Re-read the items digit by digit
> (check MOZZA BUFALA and FALAFEL). If the strip is sideways, I can re-orient it.

Loop at most ~2 times. If it still won't reconcile, **show the user both readings and ask**
rather than posting a number you can't verify. (When re-reading is blocked by orientation,
re-run `prep.py --rotate …` or `--all` from step 1 and hand over the upright image.)

### 4. Resolve the Splitwise identities (once for the batch)

- `get_current_user` → the current user's `id` (**self** / Loup) and `default_currency`.
- Load the registry for the `self`/`partner` names; find **Cassandra** and the right ledger:
  - `get_groups` → one group with both people → use it (`group_id`).
  - else `get_friends` → match the partner by name → post non-group (`group_id: 0`).
- If ambiguous (no clear group, name not found, multiple matches), show what you found and
  ask which to use. Reuse the result for every receipt.

### 5. Determine who paid (per receipt)

In priority order:
1. **CB last-4** → registry `cards`. This is *who actually paid* — the strongest signal.
2. **Loyalty identity** (`client_name` / `client_id` / `merchant`) → registry `loyalty`.
   When no PAN is printed (e.g. Monoprix prints only the EMV confirmation), the loyalty
   account is what pins the receipt to a person. Caveat: loyalty identifies the *account
   holder*, not strictly the payer — they coincide for Loup & Cassandra (each uses their
   own account), but if a CB last-4 *and* a loyalty account resolve to **different** people,
   trust the CB (who paid) and flag the conflict to the user.
3. Neither resolves (cash, faded print, unknown card/account) → **ask the user** who paid
   that specific receipt, naming the merchant and amount. Never assume silently — a wrong
   payer flips the direction of the debt. When you newly learn a card/account, offer to
   save it to the registry.

### 6. Build the split (per receipt)

```bash
python scripts/split.py <total> <self|partner>
```
Returns exact `paid_share`/`owed_share` for `self` and `partner` (odd cent → payer; the
shares are guaranteed to sum to the total, which Splitwise requires). Map `self`/`partner`
to the resolved `user_id`s.

### 7. Show the summary and wait for approval

Present a table of every receipt and **wait for an explicit OK** — a wrong expense on a
shared ledger is annoying to unwind, so this is the checkpoint.

| # | Merchant | Date | Total | Cur | Paid by | How known | Loup owes | Cassandra owes | Ledger |
|---|----------|------|-------|-----|---------|-----------|-----------|----------------|--------|

Call out anything uncertain (inferred date, sum that needed a re-read, payer asked-for) and
let the user edit before proceeding.

### 8. Create the expenses

For each approved receipt, call `create_expense` in **explicit-shares** mode (uniform across
group/non-group and either payer):
- `cost` = total · `description` = merchant (add date/city if vague)
- `currency_code` = the receipt's currency (fall back to `default_currency`)
- `date` = `YYYY-MM-DD` · `group_id` = resolved id, or `0`
- `users` = two `ExpenseUserShare` entries (self + partner) with the step-6 shares, by `user_id`
- `category_id` *(optional)*: map the receipt to a **subcategory** from `get_categories`; omit if unsure

Report what was created (merchant, amount, who owes whom) and surface any failures
distinctly — a partial batch should be obvious. Don't silently retry; you might double-post.

## Guardrails

- **Verify, then write.** The reconciliation (step 3) and the approval (step 7) are the two
  gates. Don't post a total you couldn't reconcile or that the user hasn't seen.
- **Identity registry is local & sensitive.** Card last-4s and loyalty/client names live in
  the local file only — never print full card numbers, never commit the registry.
- **Loyalty ≠ proof of payer.** It identifies the account holder; CB last-4 wins on conflict.
- **Shares must sum to the total** — always via `split.py`; never hand-round.
- **Re-runs double-post.** Splitwise has no natural dedupe; before redoing a batch, check
  recent expenses (`get_expenses`) or confirm the user wants duplicates.
- **Currency:** trust the receipt's symbol; if genuinely ambiguous, ask.

## Example

**Input:** "ajoute ce ticket sur splitwise, c'est Cassandra qui a payé" + `IMG_0228.HEIC`

1. `prep.py` → upright, compressed JPG. A Sonnet subagent exports items, discounts, totals, and the
   loyalty block: `total 23.94`, `total_crosscheck 23.94`, `tva_ttc 23.94`,
   `card_last4 null`, `loyalty {client_name:"De Carvalho", merchant_program:"Monoprix M'"}`.
2. Reconcile: `Σ items − discounts + fees` ≈ 23.94 = total = crosscheck = TTC → confident.
3. `get_current_user` → Loup; registry resolves "De Carvalho"/Monoprix → **Cassandra paid**
   (no PAN printed, loyalty pins it).
4. `split.py 23.94 partner` → Cassandra paid; each owes 11.97.
5. Show the table, get the OK, create the expense: "Monoprix 23,94 € — you owe Cassandra 11,97 €."
