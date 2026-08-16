## Run: 2026-08-16T11:45:05+00:00 — 8737b8a

### Classification
- n = 40 labeled (260 unlabeled rows skipped, out of 300 total)
- Category accuracy: 0.625
- Category F1 (macro): 0.450
- Urgency accuracy: 0.675
- Urgency F1 (macro): 0.690
- Avg confidence: 0.924

Category per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | technical_support | 0.667 | 1.000 | 0.800 | 12 |
  | product_support | 0.900 | 0.643 | 0.750 | 14 |
  | customer_service | 0.000 | 0.000 | 0.000 | 3 |
  | it_support | 0.000 | 0.000 | 0.000 | 6 |
  | billing_and_payments | 0.000 | 0.000 | 0.000 | 1 |
  | returns_and_exchanges | 0.000 | 0.000 | 0.000 | 0 |
  | service_outages_and_maintenance | 1.000 | 1.000 | 1.000 | 1 |
  | sales_and_pre_sales | 0.429 | 1.000 | 0.600 | 3 |
  | human_resources | 0.000 | 0.000 | 0.000 | 0 |
  | general_inquiry | 0.000 | 0.000 | 0.000 | 0 |

Urgency per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | low | 1.000 | 0.778 | 0.875 | 18 |
  | medium | 0.556 | 0.556 | 0.556 | 9 |
  | high | 0.667 | 0.615 | 0.640 | 13 |
  | critical | 0.000 | 0.000 | 0.000 | 0 |

## Run: 2026-08-16T17:06:58+00:00 — 8737b8a

### Classification
- n = 40 labeled (260 unlabeled rows skipped, out of 300 total)
- Category accuracy: 0.675
- Category F1 (macro): 0.540
- Urgency accuracy: 0.600
- Urgency F1 (macro): 0.606
- Avg confidence: 0.926

Category per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | technical_support | 1.000 | 0.917 | 0.957 | 12 |
  | product_support | 0.857 | 0.429 | 0.571 | 14 |
  | customer_service | 0.000 | 0.000 | 0.000 | 3 |
  | it_support | 0.545 | 1.000 | 0.706 | 6 |
  | billing_and_payments | 0.000 | 0.000 | 0.000 | 1 |
  | returns_and_exchanges | 0.000 | 0.000 | 0.000 | 0 |
  | service_outages_and_maintenance | 1.000 | 1.000 | 1.000 | 1 |
  | sales_and_pre_sales | 0.375 | 1.000 | 0.545 | 3 |
  | human_resources | 0.000 | 0.000 | 0.000 | 0 |
  | general_inquiry | 0.000 | 0.000 | 0.000 | 0 |

Urgency per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | low | 0.929 | 0.722 | 0.813 | 18 |
  | medium | 0.400 | 0.444 | 0.421 | 9 |
  | high | 0.636 | 0.538 | 0.583 | 13 |
  | critical | 0.000 | 0.000 | 0.000 | 0 |

## Run: 2026-08-16T17:10:03+00:00 — 8737b8a — **LOCKED PHASE 3 BASELINE**

### Classification
- n = 40 labeled (260 unlabeled rows skipped, out of 300 total)
- Category accuracy: 0.650
- Category F1 (macro): 0.549
- Urgency accuracy: 0.650
- Urgency F1 (macro): 0.668
- Avg confidence: 0.936

Category per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | technical_support | 1.000 | 0.833 | 0.909 | 12 |
  | product_support | 1.000 | 0.357 | 0.526 | 14 |
  | customer_service | 0.500 | 0.667 | 0.571 | 3 |
  | it_support | 0.500 | 1.000 | 0.667 | 6 |
  | billing_and_payments | 0.000 | 0.000 | 0.000 | 1 |
  | returns_and_exchanges | 0.000 | 0.000 | 0.000 | 0 |
  | service_outages_and_maintenance | 0.500 | 1.000 | 0.667 | 1 |
  | sales_and_pre_sales | 0.400 | 0.667 | 0.500 | 3 |
  | human_resources | 0.000 | 0.000 | 0.000 | 0 |
  | general_inquiry | 0.000 | 0.000 | 0.000 | 0 |

Urgency per-class:
  | label | precision | recall | f1 | support |
  |---|---|---|---|---|
  | low | 0.929 | 0.722 | 0.813 | 18 |
  | medium | 0.500 | 0.556 | 0.526 | 9 |
  | high | 0.727 | 0.615 | 0.667 | 13 |
  | critical | 0.000 | 0.000 | 0.000 | 0 |

### Investigation: category-boundary tradeoffs (2026-08-16)

Three runs above trace one investigation, run against the same 40
hand-reviewed gold-set rows via `gemini-flash-lite-latest`
(`LLM_PROVIDER=gemini`, the new default — see `agent/providers/`):

1. **Baseline** (11:45): `it_support` and `customer_service` both scored
   0% recall.
2. **+it_support fix** (17:06): added "security incidents (unauthorized
   access, data breaches/leaks, suspicious activity)" to `it_support`'s
   definition in `agent/prompts.py`. This was a genuine rubric gap, not
   ambiguity — all 6 `it_support`-ground-truth rows were security-incident
   tickets the reviewer explicitly routed there (per their own notes:
   "Active data leak elevated to high urgency," "Security vulnerability
   and unauthorized access attempt," etc.), and neither `it_support` nor
   `technical_support`'s prompt definition mentioned security/breach
   language at all. Recall: 0.000 → 1.000, with no counter-examples.
3. **+customer_service fix** (17:10, this run): added
   "marketing/promotional strategy consulting" to `customer_service`'s
   definition. Same shape of gap: the 3 `customer_service`-ground-truth
   rows were all digital-marketing-strategy tickets with no matching
   language anywhere in the rubric. Recall: 0.000 → 0.667.

**Both fixes cost recall elsewhere**: `product_support` recall fell
0.643 → 0.357 and `technical_support` 1.000 → 0.833 across the three
runs. This was investigated by re-classifying every `product_support`/
`technical_support` ground-truth row and inspecting the 9 resulting
misses directly (not via a further eval-harness run). Conclusion: **this
residual drop is category-boundary ambiguity, not a further rubric gap**,
based on three findings:

- **The advisory-security wording has no consistent signal to key off.**
  `ticket-002566` ("request comprehensive guidance on securing medical
  data... best practices") is ground-truth `it_support` (reviewer note:
  "Compliance and best practices inquiry" — explicitly not an incident).
  `ticket-013478` and `ticket-021713` are near-identical in phrasing
  ("offer details on securing medical information," "seeking advice on
  securing medical data... security measures") yet are ground-truth
  `product_support`. An "active incident vs. advisory guidance" qualifier
  was drafted and rejected: it would fix the latter two but break
  `ticket-002566`, a net wash dressed up as a fix.
- **`it_support`'s original "API keys/integrations" clause pre-dates
  today's changes and structurally overlaps `product_support`'s "feature
  usage" and `technical_support`'s "bugs."** Tickets like "problem with
  JIRA integration API" (technical_support) and "how do I integrate Keras
  Docker" (product_support) collide with it_support's integrations
  language. Not introduced by today's edits.
- **Several "digital marketing" tickets are near-duplicate phrasing with
  different ground truth** — e.g. `ticket-008262` ("enhance digital
  marketing strategies... social media campaigns") is `product_support`,
  while `ticket-002660` ("Revise Digital Marketing Initiatives") is
  `customer_service`. No rubric wording distinguishes them.

**Decision: the prompt is locked as of this run.** No further changes
without new gold-set evidence — the remaining errors are boundary
tradeoffs and (in places) inconsistent human labeling on ambiguous
synthetic tickets, not a bounded gap a rubric tweak can close.

**Caveats on this baseline**: n=40 total, and several categories have
support of 0-3 (`customer_service`=3, `it_support`=6,
`billing_and_payments`=1, `service_outages_and_maintenance`=1,
`returns_and_exchanges`/`human_resources`/`general_inquiry`=0 — no gold
rows landed in these three at all in this 40-row subset). Per-class
precision/recall at this n swings 33-100% on a single ticket and should
be read as directional, not a tight estimate. Urgency metrics fluctuated
run-to-run (0.675 → 0.600 → 0.650) despite no urgency-related prompt
changes across any of the three runs — that movement is model sampling
noise (calls are not temperature-0), not signal.

