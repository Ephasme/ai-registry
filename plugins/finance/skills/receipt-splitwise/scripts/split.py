#!/usr/bin/env python3
"""Compute a 50/50 split for one receipt, guaranteeing the shares sum exactly.

Splitwise's create_expense rejects an expense unless the participants' paid
shares sum to the cost AND their owed shares sum to the cost. With an odd number
of cents a naive `cost / 2` produces two halves that don't add back up, so this
helper does the rounding deterministically: each person owes half, and the leftover
cent (if any) is charged to whoever paid — they fronted the money, they eat the
rounding.

Usage:
    python split.py <total> <self|partner>

    <total>  receipt total. Dot or comma decimal, optional currency sign:
             "25.01", "25,01", "€25,01" all work.
    <payer>  "self" (the current Splitwise user, e.g. Loup) or "partner"
             (the other person, e.g. Cassandra) — whoever paid the full amount.

Prints one line of JSON to stdout, e.g. for `python split.py 25.01 self`:

    {"cost": "25.01", "payer": "self",
     "self":    {"paid_share": "25.01", "owed_share": "12.51"},
     "partner": {"paid_share": "0.00",  "owed_share": "12.50"}}

Map `self`/`partner` to the resolved Splitwise user_ids when building the
create_expense `users` payload.
"""
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

CENT = Decimal("0.01")


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in ("self", "partner"):
        sys.exit("usage: python split.py <total> <self|partner>")

    raw = sys.argv[1].replace(",", ".")
    raw = "".join(c for c in raw if c.isdigit() or c == ".").strip()
    payer = sys.argv[2]

    try:
        cost = Decimal(raw).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        sys.exit(f"could not parse a total from {sys.argv[1]!r}")
    if cost <= 0:
        sys.exit(f"total must be positive, got {cost}")

    smaller_half = (cost / 2).quantize(CENT, rounding=ROUND_DOWN)
    larger_half = cost - smaller_half  # carries the odd cent

    # The payer absorbs the odd cent (the larger half).
    payer_owed, other_owed = larger_half, smaller_half

    self_is_payer = payer == "self"
    result = {
        "cost": f"{cost:.2f}",
        "payer": payer,
        "self": {
            "paid_share": f"{(cost if self_is_payer else Decimal(0)):.2f}",
            "owed_share": f"{(payer_owed if self_is_payer else other_owed):.2f}",
        },
        "partner": {
            "paid_share": f"{(Decimal(0) if self_is_payer else cost):.2f}",
            "owed_share": f"{(other_owed if self_is_payer else payer_owed):.2f}",
        },
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
