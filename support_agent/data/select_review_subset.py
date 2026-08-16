"""Select a small, stratified subset of the gold set for hand review.

Hand-reviewing all 300 rows of data/gold_set.jsonl isn't practical to do
in one sitting, so this picks a smaller, stratified sample (default n=40,
covering all 30 (category, urgency) strata) and exports it as a plain-text
review sheet (data/review_subset.md) that a human fills in directly.

Uses `_allocate_with_minimum` rather than build_gold_set.py's strict
proportional `_allocate_strata`: at n=40 across 30 strata, pure
proportional allocation starves the smallest strata down to 0 (the same
rounding issue Phase 1 hit at n=200, documented in DATA_CARD.md) — and for
a review batch this small, having a full category's worth of tickets
completely absent from the eval is worse than a slightly less
proportional sample. Every stratum gets at least 1 slot; the rest is
distributed proportionally by largest remainder.

apply_review.py (run separately, after the sheet is filled in) reads it
back and writes corrections into data/gold_set.jsonl's human_label field
for just those rows — the rest stay null until reviewed in a future pass.
"""

from __future__ import annotations

import random
from pathlib import Path

from support_agent.data.build_gold_set import load_gold_set
from support_agent.schemas import Category, GoldSetRow, Urgency

REVIEW_SHEET_PATH = Path(__file__).parent / "review_subset.md"

DEFAULT_REVIEW_SIZE = 40
# Different seed from build_gold_set.py's 42 so this draws an independent
# sub-sample rather than always picking the same rows in the same order.
DEFAULT_SEED = 7


def _allocate_with_minimum(
    strata_sizes: dict[tuple[Category, Urgency], int], n: int, minimum: int = 1
) -> dict[tuple[Category, Urgency], int]:
    """Proportional allocation (largest-remainder) with a guaranteed floor per stratum.

    Requires n >= len(strata_sizes) * minimum. Every stratum is assumed to
    already have size >= minimum (true here: a stratum only exists in
    strata_sizes because at least one row landed in it).
    """
    if n < len(strata_sizes) * minimum:
        raise ValueError(
            f"n={n} is too small to give all {len(strata_sizes)} strata a minimum of {minimum} each"
        )

    guaranteed = dict.fromkeys(strata_sizes, minimum)
    remaining = n - sum(guaranteed.values())
    leftover_capacity = {key: size - minimum for key, size in strata_sizes.items()}
    total_leftover = sum(leftover_capacity.values())

    if remaining == 0 or total_leftover == 0:
        return guaranteed

    raw = {key: remaining * cap / total_leftover for key, cap in leftover_capacity.items()}
    extra = {key: int(value) for key, value in raw.items()}
    extra_remainder = remaining - sum(extra.values())
    by_fraction = sorted(raw.keys(), key=lambda k: (raw[k] - extra[k], str(k)), reverse=True)
    for key in by_fraction[:extra_remainder]:
        extra[key] += 1

    return {key: min(guaranteed[key] + extra[key], strata_sizes[key]) for key in strata_sizes}


def select_review_subset(
    rows: list[GoldSetRow], n: int = DEFAULT_REVIEW_SIZE, seed: int = DEFAULT_SEED
) -> list[GoldSetRow]:
    rng = random.Random(seed)

    strata: dict[tuple[Category, Urgency], list[GoldSetRow]] = {}
    for row in rows:
        strata.setdefault((row.weak_category, row.weak_urgency), []).append(row)

    allocation = _allocate_with_minimum({key: len(group) for key, group in strata.items()}, n)

    selected: list[GoldSetRow] = []
    for key, count in allocation.items():
        group = strata[key]
        selected.extend(rng.sample(group, count))

    rng.shuffle(selected)
    return selected


def format_review_sheet(rows: list[GoldSetRow]) -> str:
    valid_categories = ", ".join(c.value for c in Category)
    valid_urgencies = ", ".join(u.value for u in Urgency)

    header = f"""# Gold set hand-review sheet ({len(rows)} tickets)

For each ticket below, read the subject/body and decide whether the weak
label (taken from the dataset's own `queue`/`priority` fields) is
correct.

- Change REVIEWED from "no" to "yes" once you've made a decision on that \
ticket — this is what tells apply_review.py you actually looked at it, \
since blank correction fields alone can't distinguish "confirmed correct" \
from "haven't gotten to this one yet". Rows still marked "no" are skipped \
and reported, not guessed at.
- If the weak label is correct: leave CORRECTED_CATEGORY / \
CORRECTED_URGENCY blank.
- If it's wrong: write the correct value on that line.
- NOTES is optional — use it for anything worth flagging (ambiguous \
ticket, borderline urgency, etc).

Valid categories: {valid_categories}
Valid urgencies: {valid_urgencies}

Do not remove or edit the "### ticket-XXXXXX" lines — apply_review.py \
matches rows by that exact id. When you're done, save this file and ask \
Claude to run `python -m support_agent.data.apply_review`.

---

"""
    blocks = [
        (
            f"### {row.ticket_id}\n"
            f"Subject: {row.subject or '(no subject)'}\n\n"
            f"Body:\n{row.body}\n\n"
            f"Weak label: category={row.weak_category.value}, urgency={row.weak_urgency.value}\n\n"
            f"REVIEWED: no\n"
            f"CORRECTED_CATEGORY: \n"
            f"CORRECTED_URGENCY: \n"
            f"NOTES: \n"
        )
        for row in rows
    ]
    return header + "\n---\n\n".join(blocks) + "\n"


def write_review_sheet(rows: list[GoldSetRow], path: Path = REVIEW_SHEET_PATH) -> None:
    path.write_text(format_review_sheet(rows), encoding="utf-8")
    print(f"[select_review_subset] Wrote {len(rows)} tickets to {path}")


if __name__ == "__main__":
    subset = select_review_subset(load_gold_set())
    write_review_sheet(subset)
