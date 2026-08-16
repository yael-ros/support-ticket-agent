"""Apply a completed review sheet (data/review_subset.md) back into gold_set.jsonl.

Parses each "### ticket-XXXXXX" block, and for blocks marked
`REVIEWED: yes`, writes a `HumanLabel` into the matching row of
data/gold_set.jsonl: `CORRECTED_CATEGORY`/`CORRECTED_URGENCY` become
overrides if non-blank, or `None` (meaning "weak label confirmed
correct") if left blank. Blocks still marked `REVIEWED: no` are skipped
and reported — never silently treated as either reviewed or unreviewed by
guesswork.

Rows in gold_set.jsonl that aren't in the review sheet at all are left
completely untouched, including any `human_label` from a prior review
round — this script only ever adds/updates labels for rows present in the
sheet being applied.
"""

from __future__ import annotations

import re
from pathlib import Path

from support_agent.data.build_gold_set import GOLD_SET_PATH, load_gold_set, write_gold_set
from support_agent.data.select_review_subset import REVIEW_SHEET_PATH
from support_agent.schemas import Category, HumanLabel, Urgency

_FIELD_PATTERN = re.compile(r"^(REVIEWED|CORRECTED_CATEGORY|CORRECTED_URGENCY|NOTES):\s*(.*)$")
_TICKET_HEADER_PATTERN = re.compile(r"^### ", re.MULTILINE)


class ReviewSheetError(Exception):
    """Raised when the review sheet contains a value apply_review.py can't parse."""


def parse_review_sheet(text: str) -> dict[str, HumanLabel | None]:
    """Return {ticket_id: HumanLabel} for reviewed blocks; unreviewed blocks are omitted.

    Raises ReviewSheetError if a reviewed block has an unrecognized
    category/urgency value (likely a typo) — better to fail loudly and
    name the offending ticket than to silently drop or misapply it.
    """
    # Anchored to line start: the sheet's own instructions text mentions
    # the literal string "### ticket-XXXXXX" mid-paragraph (see
    # select_review_subset.py's format_review_sheet), and a naive
    # substring split on "### " would misparse that sentence as a
    # phantom ticket block.
    blocks = _TICKET_HEADER_PATTERN.split(text)[1:]
    reviewed: dict[str, HumanLabel | None] = {}

    for block in blocks:
        lines = block.strip().splitlines()
        ticket_id = lines[0].strip()

        fields = {"REVIEWED": "no", "CORRECTED_CATEGORY": "", "CORRECTED_URGENCY": "", "NOTES": ""}
        for line in lines[1:]:
            match = _FIELD_PATTERN.match(line.strip())
            if match:
                key, value = match.groups()
                fields[key] = value.strip()

        if fields["REVIEWED"].lower() not in ("yes", "y", "true"):
            continue

        raw_category = fields["CORRECTED_CATEGORY"]
        raw_urgency = fields["CORRECTED_URGENCY"]

        category = None
        if raw_category:
            try:
                category = Category(raw_category)
            except ValueError as exc:
                raise ReviewSheetError(
                    f"{ticket_id}: CORRECTED_CATEGORY {raw_category!r} is not a valid Category "
                    f"({', '.join(c.value for c in Category)})"
                ) from exc

        urgency = None
        if raw_urgency:
            try:
                urgency = Urgency(raw_urgency)
            except ValueError as exc:
                raise ReviewSheetError(
                    f"{ticket_id}: CORRECTED_URGENCY {raw_urgency!r} is not a valid Urgency "
                    f"({', '.join(u.value for u in Urgency)})"
                ) from exc

        reviewed[ticket_id] = HumanLabel(category=category, urgency=urgency, notes=fields["NOTES"] or None)

    return reviewed


def apply_review(
    sheet_path: Path = REVIEW_SHEET_PATH, gold_set_path: Path = GOLD_SET_PATH
) -> tuple[int, int]:
    """Returns (n_applied, n_still_unreviewed_in_sheet)."""
    reviewed = parse_review_sheet(sheet_path.read_text(encoding="utf-8"))

    rows = load_gold_set(gold_set_path)
    sheet_ticket_ids = set(_extract_all_ticket_ids(sheet_path.read_text(encoding="utf-8")))
    n_still_unreviewed = len(sheet_ticket_ids - reviewed.keys())

    applied = 0
    updated_rows = []
    for row in rows:
        if row.ticket_id in reviewed:
            row = row.model_copy(update={"human_label": reviewed[row.ticket_id]})
            applied += 1
        updated_rows.append(row)

    write_gold_set(updated_rows, gold_set_path)
    return applied, n_still_unreviewed


def _extract_all_ticket_ids(text: str) -> list[str]:
    return [block.strip().splitlines()[0].strip() for block in _TICKET_HEADER_PATTERN.split(text)[1:]]


if __name__ == "__main__":
    n_applied, n_pending = apply_review()
    print(f"[apply_review] Applied {n_applied} reviewed labels to {GOLD_SET_PATH}")
    if n_pending:
        print(f"[apply_review] {n_pending} tickets in the sheet are still marked REVIEWED: no")
