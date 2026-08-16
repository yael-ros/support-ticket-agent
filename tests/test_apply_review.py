import pytest

from support_agent.data.apply_review import ReviewSheetError, apply_review, parse_review_sheet
from support_agent.data.build_gold_set import load_gold_set, write_gold_set
from support_agent.schemas import Category, GoldSetRow, HumanLabel, Urgency

SAMPLE_SHEET = """# Gold set hand-review sheet (3 tickets)

Some instructions here.

---

### ticket-000001
Subject: Can't log in
Body:
SSO redirect loop.

Weak label: category=it_support, urgency=high

REVIEWED: yes
CORRECTED_CATEGORY:
CORRECTED_URGENCY:
NOTES: confirmed correct

---

### ticket-000002
Subject: Refund question
Body:
Where is my refund?

Weak label: category=technical_support, urgency=low

REVIEWED: yes
CORRECTED_CATEGORY: returns_and_exchanges
CORRECTED_URGENCY: medium
NOTES: weak label was wrong, this is clearly a refund question

---

### ticket-000003
Subject: Something else
Body:
Haven't gotten to this one.

Weak label: category=general_inquiry, urgency=low

REVIEWED: no
CORRECTED_CATEGORY:
CORRECTED_URGENCY:
NOTES:
"""


def test_parse_review_sheet_confirmed_row_yields_empty_human_label():
    reviewed = parse_review_sheet(SAMPLE_SHEET)
    assert reviewed["ticket-000001"] == HumanLabel(category=None, urgency=None, notes="confirmed correct")


def test_parse_review_sheet_corrected_row_yields_overrides():
    reviewed = parse_review_sheet(SAMPLE_SHEET)
    label = reviewed["ticket-000002"]
    assert label.category == Category.RETURNS_AND_EXCHANGES
    assert label.urgency == Urgency.MEDIUM


def test_parse_review_sheet_skips_unreviewed_rows():
    reviewed = parse_review_sheet(SAMPLE_SHEET)
    assert "ticket-000003" not in reviewed


def test_parse_review_sheet_ignores_header_text_mentioning_ticket_header_literal():
    # The real sheet's instructions paragraph contains the literal string
    # '"### ticket-XXXXXX"' mid-sentence (see select_review_subset.py's
    # format_review_sheet). A naive substring split on "### " misparses
    # that sentence as a phantom ticket block; the header-anchored split
    # must not.
    sheet = (
        'Do not remove or edit the "### ticket-XXXXXX" lines.\n\n---\n\n' + SAMPLE_SHEET.split("---\n\n", 1)[1]
    )
    reviewed = parse_review_sheet(sheet)
    assert set(reviewed.keys()) == {"ticket-000001", "ticket-000002"}


def test_parse_review_sheet_invalid_category_raises():
    bad_sheet = SAMPLE_SHEET.replace(
        "CORRECTED_CATEGORY: returns_and_exchanges", "CORRECTED_CATEGORY: not_a_real_category"
    )
    with pytest.raises(ReviewSheetError, match="ticket-000002"):
        parse_review_sheet(bad_sheet)


def test_apply_review_end_to_end(tmp_path):
    sheet_path = tmp_path / "review_subset.md"
    sheet_path.write_text(SAMPLE_SHEET, encoding="utf-8")

    gold_set_path = tmp_path / "gold_set.jsonl"
    rows = [
        GoldSetRow(
            ticket_id="ticket-000001",
            subject="Can't log in",
            body="SSO redirect loop.",
            weak_category=Category.IT_SUPPORT,
            weak_urgency=Urgency.HIGH,
        ),
        GoldSetRow(
            ticket_id="ticket-000002",
            subject="Refund question",
            body="Where is my refund?",
            weak_category=Category.TECHNICAL_SUPPORT,
            weak_urgency=Urgency.LOW,
        ),
        GoldSetRow(
            ticket_id="ticket-000003",
            subject="Something else",
            body="Haven't gotten to this one.",
            weak_category=Category.GENERAL_INQUIRY,
            weak_urgency=Urgency.LOW,
        ),
        GoldSetRow(
            # Not in the sheet at all — must be left completely untouched,
            # including its pre-existing human_label from a prior round.
            ticket_id="ticket-000004",
            subject="Already reviewed earlier",
            body="...",
            weak_category=Category.SALES_AND_PRE_SALES,
            weak_urgency=Urgency.LOW,
            human_label=HumanLabel(notes="reviewed in round 1"),
        ),
    ]
    write_gold_set(rows, gold_set_path)

    n_applied, n_pending = apply_review(sheet_path=sheet_path, gold_set_path=gold_set_path)

    assert n_applied == 2
    assert n_pending == 1

    result_rows = {r.ticket_id: r for r in load_gold_set(gold_set_path)}
    assert result_rows["ticket-000001"].human_label.notes == "confirmed correct"
    assert result_rows["ticket-000002"].human_label.category == Category.RETURNS_AND_EXCHANGES
    assert result_rows["ticket-000003"].human_label is None  # still unreviewed
    assert result_rows["ticket-000004"].human_label.notes == "reviewed in round 1"  # untouched
