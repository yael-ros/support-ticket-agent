"""Build a stratified, hand-reviewable gold set for evaluation.

Samples ~300 tickets stratified by (category, urgency) — 30 strata in the
English-language subset, all populated (see data/DATA_CARD.md) — using
proportional allocation (largest-remainder rounding) so each stratum's
representation in the sample matches its share of the full dataset. n=300
(rather than the originally planned 200) is what it takes for the two
smallest strata (human_resources×high, general_inquiry×high, each <0.3%
of the dataset) to round up to at least 1 row instead of 0.

IMPORTANT — this file is not ground truth. Every row's `human_label` field
is written as null. This gold set is meant to be hand-corrected by the
developer before any eval script scores against it (see
.claude/skills/eval-harness). The dataset's own `queue`/`priority` fields
(surfaced here as `weak_category`/`weak_urgency`) are weak supervision, not
verified truth — they come from whatever process originally triaged the
ticket, which we have no visibility into.
"""

from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

from support_agent.data.load_tickets import load_and_normalize_tickets
from support_agent.schemas import Category, GoldSetRow, Ticket, Urgency

GOLD_SET_PATH = Path(__file__).parent / "gold_set.jsonl"

DEFAULT_SAMPLE_SIZE = 300
DEFAULT_SEED = 42


def _allocate_strata(
    strata_sizes: dict[tuple[Category, Urgency], int], n: int
) -> dict[tuple[Category, Urgency], int]:
    """Proportional allocation of `n` samples across strata (largest-remainder method).

    Guarantees the returned allocation sums to exactly `n` (assuming
    n <= total population) and never allocates more than a stratum's size.
    """
    total = sum(strata_sizes.values())
    raw = {key: n * size / total for key, size in strata_sizes.items()}
    floors = {key: int(value) for key, value in raw.items()}
    remainder = n - sum(floors.values())

    # Distribute leftover slots to the strata with the largest fractional
    # remainder, breaking ties by stratum key for determinism.
    by_fraction = sorted(raw.keys(), key=lambda k: (raw[k] - floors[k], str(k)), reverse=True)
    for key in by_fraction[:remainder]:
        floors[key] += 1

    for key, count in floors.items():
        floors[key] = min(count, strata_sizes[key])

    return floors


def build_gold_set(
    tickets: list[Ticket], n: int = DEFAULT_SAMPLE_SIZE, seed: int = DEFAULT_SEED
) -> list[GoldSetRow]:
    """Stratified sample of `n` tickets by (category, urgency), as GoldSetRow."""
    rng = random.Random(seed)

    strata: dict[tuple[Category, Urgency], list[Ticket]] = defaultdict(list)
    for ticket in tickets:
        strata[(ticket.category, ticket.urgency)].append(ticket)

    allocation = _allocate_strata({key: len(group) for key, group in strata.items()}, n)

    sampled: list[Ticket] = []
    for key, count in allocation.items():
        group = strata[key]
        sampled.extend(rng.sample(group, count))

    rng.shuffle(sampled)

    return [
        GoldSetRow(
            ticket_id=ticket.id,
            subject=ticket.subject,
            body=ticket.body,
            reference_answer=ticket.answer,
            weak_category=ticket.category,
            weak_urgency=ticket.urgency,
            human_label=None,
        )
        for ticket in sampled
    ]


def write_gold_set(rows: list[GoldSetRow], path: Path = GOLD_SET_PATH) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(row.model_dump_json() + "\n")

    print(f"[build_gold_set] Wrote {len(rows)} rows to {path}")
    print(
        "[build_gold_set] REMINDER: every row's `human_label` field is null. "
        "This file is weak-supervision only — hand-correct `human_label` for "
        "each row before it is used by any eval script."
    )


if __name__ == "__main__":
    all_tickets = load_and_normalize_tickets()
    gold_rows = build_gold_set(all_tickets)
    write_gold_set(gold_rows)
