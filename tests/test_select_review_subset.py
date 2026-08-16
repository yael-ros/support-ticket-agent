from support_agent.data.select_review_subset import format_review_sheet, select_review_subset
from support_agent.schemas import Category, GoldSetRow, Urgency


def _row(ticket_id, category, urgency):
    return GoldSetRow(
        ticket_id=ticket_id,
        subject=f"subject {ticket_id}",
        body=f"body {ticket_id}",
        weak_category=category,
        weak_urgency=urgency,
    )


def test_select_review_subset_returns_requested_size_without_duplicates():
    rows = [
        _row(f"t{i}", Category.TECHNICAL_SUPPORT if i % 2 == 0 else Category.BILLING_AND_PAYMENTS, Urgency.LOW)
        for i in range(100)
    ]
    subset = select_review_subset(rows, n=20, seed=1)
    assert len(subset) == 20
    assert len({r.ticket_id for r in subset}) == 20


def test_select_review_subset_reproducible_with_fixed_seed():
    rows = [_row(f"t{i}", Category.IT_SUPPORT, Urgency.MEDIUM) for i in range(50)]
    a = select_review_subset(rows, n=10, seed=5)
    b = select_review_subset(rows, n=10, seed=5)
    assert [r.ticket_id for r in a] == [r.ticket_id for r in b]


def test_select_review_subset_guarantees_every_stratum_at_least_one_row():
    # A tiny stratum (2 rows) alongside a huge one (200 rows) — pure
    # proportional allocation at n=20 would round the tiny stratum to 0.
    rows = [_row(f"big{i}", Category.TECHNICAL_SUPPORT, Urgency.LOW) for i in range(200)]
    rows += [_row(f"tiny{i}", Category.HUMAN_RESOURCES, Urgency.HIGH) for i in range(2)]

    subset = select_review_subset(rows, n=20, seed=1)
    strata_present = {(r.weak_category, r.weak_urgency) for r in subset}
    assert (Category.HUMAN_RESOURCES, Urgency.HIGH) in strata_present


def test_format_review_sheet_contains_every_ticket_id_and_reviewed_marker():
    rows = [_row("ticket-000001", Category.IT_SUPPORT, Urgency.HIGH)]
    sheet = format_review_sheet(rows)
    assert "### ticket-000001" in sheet
    assert "REVIEWED: no" in sheet
    assert "CORRECTED_CATEGORY:" in sheet
    assert "CORRECTED_URGENCY:" in sheet
