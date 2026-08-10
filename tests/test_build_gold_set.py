from support_agent.data.build_gold_set import _allocate_strata, build_gold_set
from support_agent.schemas import Category, Ticket, Urgency


def _make_ticket(i: int, category: Category, urgency: Urgency) -> Ticket:
    return Ticket(
        id=f"ticket-{i:06d}",
        subject=f"Subject {i}",
        body=f"Body text {i}",
        answer=f"Answer {i}",
        category=category,
        urgency=urgency,
        language="en",
        ticket_type="Incident",
        raw_queue=category.value,
        raw_priority=urgency.value,
    )


def test_allocate_strata_sums_to_n():
    strata_sizes = {
        (Category.TECHNICAL_SUPPORT, Urgency.LOW): 100,
        (Category.TECHNICAL_SUPPORT, Urgency.HIGH): 50,
        (Category.HUMAN_RESOURCES, Urgency.LOW): 7,
    }
    allocation = _allocate_strata(strata_sizes, n=20)
    assert sum(allocation.values()) == 20
    for key, count in allocation.items():
        assert count <= strata_sizes[key]


def test_allocate_strata_never_exceeds_stratum_size():
    # A tiny stratum shouldn't be over-allocated even if its proportional
    # share would round up past its actual population.
    strata_sizes = {
        (Category.TECHNICAL_SUPPORT, Urgency.LOW): 1000,
        (Category.HUMAN_RESOURCES, Urgency.CRITICAL): 1,
    }
    allocation = _allocate_strata(strata_sizes, n=50)
    assert allocation[(Category.HUMAN_RESOURCES, Urgency.CRITICAL)] <= 1
    assert sum(allocation.values()) <= sum(strata_sizes.values())


def test_build_gold_set_produces_requested_sample_size_and_null_human_label():
    tickets = []
    idx = 0
    for category in [Category.TECHNICAL_SUPPORT, Category.BILLING_AND_PAYMENTS]:
        for urgency in [Urgency.LOW, Urgency.MEDIUM, Urgency.HIGH]:
            for _ in range(20):
                tickets.append(_make_ticket(idx, category, urgency))
                idx += 1

    rows = build_gold_set(tickets, n=30, seed=1)
    assert len(rows) == 30
    assert all(row.human_label is None for row in rows)
    # No duplicate tickets sampled
    assert len({row.ticket_id for row in rows}) == 30


def test_build_gold_set_is_reproducible_with_fixed_seed():
    tickets = [_make_ticket(i, Category.TECHNICAL_SUPPORT, Urgency.LOW) for i in range(50)]
    rows_a = build_gold_set(tickets, n=10, seed=42)
    rows_b = build_gold_set(tickets, n=10, seed=42)
    assert [r.ticket_id for r in rows_a] == [r.ticket_id for r in rows_b]
