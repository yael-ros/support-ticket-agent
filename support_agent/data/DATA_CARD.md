# Data Card: Support Ticket Dataset (Phase 1)

## Provenance

- **Source:** Hugging Face [`Tobi-Bueck/customer-support-tickets`](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets)
- **Raw size:** 61,765 rows
- **Raw schema:** `subject`, `body`, `answer`, `type`, `queue`, `priority`,
  `language`, `version`, `tag_1`..`tag_8`
- **Format:** email-style support tickets (subject + body), each paired with
  the historical agent's actual reply (`answer`). This is **not** a chat/
  multi-turn dataset — there is no back-and-forth thread, just one ticket
  and one response.
- Loaded via the `datasets` library. Cache location is the library's own
  default (`~/.cache/huggingface/datasets`), not a repo-local directory —
  see the "Windows path-length" note below.

## Filtering (v1 scope)

| Step | Rows |
|---|---|
| Raw dataset | 61,765 |
| Filtered to `language == "en"` | 28,261 |
| Dropped: empty/null `body` | 1 |
| **Final normalized ticket count** | **28,260** |

Non-English rows (33,504, all `language == "de"`) are dropped entirely for
v1, not translated — out of scope per BUILD_PLAN.md.

## Normalization

### Category (from raw `queue`)

The English-language subset contains **exactly 10 distinct `queue` values**,
all mapped 1:1 to `Category` enum members (see `support_agent/schemas.py`
and `QUEUE_TO_CATEGORY` in `load_tickets.py`):

| Raw `queue` | Category | Count (EN) |
|---|---|---|
| Technical Support | `technical_support` | 8,149 |
| Product Support | `product_support` | 5,305 |
| Customer Service | `customer_service` | 4,269 |
| IT Support | `it_support` | 3,333 |
| Billing and Payments | `billing_and_payments` | 2,897 |
| Returns and Exchanges | `returns_and_exchanges` | 1,402 |
| Service Outages and Maintenance | `service_outages_and_maintenance` | 1,106 |
| Sales and Pre-Sales | `sales_and_pre_sales` | 843 |
| Human Resources | `human_resources` | 553 |
| General Inquiry | `general_inquiry` | 404 |

**Known limitation:** the full (multi-language) dataset has ~40 additional
long-tail `queue` values (e.g. `"Pets & Animals/Veterinary Care"`,
`"Health/Mental Health"`) that appear **only** in the German-language rows.
These never surface in v1 since we filter to English first, but if a future
data refresh introduced English rows with these values, they would fall
through to `Category.GENERAL_INQUIRY` at ingestion (logged as a warning,
not silently dropped — see `normalize_category`).

### Urgency (from raw `priority`)

The English-language subset only contains **{low, medium, high}** — no
`critical` or `very_low` rows. Those two values exist only among the
dataset's German-language rows (`critical`: 1,914 rows; `very_low`: 1,783
rows, both German-only). `Urgency.CRITICAL` is still defined in the schema
for forward-compatibility, but **no v1 gold-set or ticket row will carry
it.** This is a meaningful gap: the eval set cannot currently measure
classification accuracy on the highest-urgency tier.

| Raw `priority` | Urgency | Count (EN) |
|---|---|---|
| low | `low` | 5,774 |
| medium | `medium` | 11,570 |
| high | `high` | 10,917 |
| critical | `critical` | 0 (EN) — 1,914 (DE only) |
| very_low → low | `low` | 0 (EN) — 1,783 (DE only) |

**Ground truth caveat:** `priority` is the dataset's own field, produced by
whatever process originally triaged each ticket (unknown to us — possibly a
human agent, possibly a heuristic, possibly synthetic). It is treated
throughout this project as **weak supervision, not verified truth**. The
same caveat applies to `queue`. This is why `data/gold_set.jsonl` exists —
to let a human hand-correct a sample before it's used for real evaluation.

## Known limitations

1. **Email, not chat.** Single-turn subject+body+answer triples, no
   multi-message thread context.
2. **No independent urgency ground truth.** `priority` is weak supervision
   only (see above).
3. **No `critical` urgency in English data.** The urgency classifier and
   its eval can only be validated on low/medium/high in v1.
4. **~13% of English rows have an empty `subject`** (3,639 / 28,261),
   normalized to `""` rather than dropped.
5. **~6 English rows have a null `answer`** — kept as `None`; these
   tickets have no historical reference response for eval comparison.
6. **Duplicate/near-duplicate ticket bodies:** ~4,596 of 28,261 English
   `body` values are exact string duplicates of another row (likely
   templated/synthetic tickets in the source dataset). Not deduplicated in
   v1 — retrieval/classification eval numbers should be read with this in
   mind, as it may inflate apparent accuracy for common templates.
7. **Windows path-length constraint (environment note, not a data
   limitation):** this repo's directory nesting, combined with the
   `datasets` library's Windows lock-file naming (which embeds the full
   resolved cache path twice), exceeds the 260-char `MAX_PATH` limit if the
   cache is placed in a repo-local directory. `load_tickets.py` therefore
   uses the library's own default cache location instead of
   `support_agent/data/cache/`. Still fully local, still gitignored by
   virtue of living outside the repo — no external service required.

## Gold set (`data/gold_set.jsonl`)

- **Method:** stratified sampling by (category, urgency) — 30 strata, all
  populated in the full English dataset — using proportional allocation
  with largest-remainder rounding (`_allocate_strata` in
  `build_gold_set.py`). Seed: 42 (reproducible).
- **Size:** 300 rows (see actual counts below). Originally 200, bumped to
  300 because proportional allocation at n=200 rounded the two smallest
  strata down to zero (see below) — 300 is the smallest round number at
  which both recover at least 1 row each.
- **Coverage:** **30 of 30 strata represented** — confirmed by
  enumerating all (category, urgency) pairs present in the filtered
  dataset and checking each has ≥1 sampled row. The two previously-missing
  strata — `human_resources`×`high` (58 tickets, 0.2% of the dataset) and
  `general_inquiry`×`high` (66 tickets, 0.2%) — now have exactly 1 row
  each; they remain the thinnest strata in the sample and any per-class
  metric computed on them will be high-variance (n=1).
- **`human_label` field:** null on every row, by design. **This file is not
  ground truth as shipped** — it must be hand-corrected before any eval
  script scores against it (enforced by `.claude/skills/eval-harness`,
  which requires eval scripts to refuse to run against rows where
  `human_label` is null).

### Gold set category distribution (n=300)

| Category | Count |
|---|---|
| technical_support | 86 |
| product_support | 57 |
| customer_service | 45 |
| it_support | 35 |
| billing_and_payments | 31 |
| returns_and_exchanges | 14 |
| service_outages_and_maintenance | 12 |
| sales_and_pre_sales | 9 |
| human_resources | 6 |
| general_inquiry | 5 |

### Gold set urgency distribution (n=300)

| Urgency | Count |
|---|---|
| medium | 122 |
| high | 116 |
| low | 62 |
| critical | 0 (none exist in EN data — see above) |

## Reproducing this

```
python -m support_agent.data.build_gold_set
```

Regenerates `data/gold_set.jsonl` from scratch with seed=42 (deterministic
given the same underlying dataset). **This will overwrite any hand
corrections already made to `human_label`** — do not re-run after starting
manual review without backing up the reviewed file first.
