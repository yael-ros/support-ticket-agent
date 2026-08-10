---
name: eval-harness
description: Use this skill whenever adding a new evaluation metric, updating the gold set, regenerating eval reports, or when asked to "run the evals," "check the numbers," or "update the eval report" for the support ticket agent. Covers the required report format and the rule against fabricating metrics.
---

# Eval Harness Conventions

This project's credibility rests on its evaluation numbers being real and
reproducible. Follow these rules whenever touching anything under
`evaluation/` or `data/gold_set.jsonl`.

## Before running any eval

1. Confirm `data/gold_set.jsonl` has human-corrected labels (a `human_label`
   field that is not null) for the rows you're evaluating against. If it
   doesn't, stop and say so — do not evaluate against unlabeled weak
   supervision and report it as ground truth.
2. Confirm the KB index is built and up to date
   (`knowledge_base/build_index.py` has been run since the last doc change).

## Report format

Every eval run appends a timestamped entry to `eval/results/full_report.md`
with this structure — do not overwrite previous entries, so the report
becomes a run-over-run history:

```
## Run: <ISO timestamp> — <git short SHA>

### Classification
- Category accuracy: X% (n=<gold set size>)
- Category F1 (macro): X
- Urgency accuracy: X%
- Urgency F1 (macro): X

### Retrieval
- Precision@3: X
- Recall@5: X

### Generation (LLM-as-judge, rubric v<N>)
- Helpfulness: X/5 (avg)
- Correctness: X/5 (avg)
- Tone: X/5 (avg)

### Operations
- Auto-send rate at threshold=<value>: X%
- Avg latency per ticket: X s
- Est. cost per ticket: $X
```

## Rules

- Never hand-write numbers into this file. They must come from an actual
  script run. If asked to "add eval results," run the script.
- If a metric regresses more than 5 points from the previous run, flag it
  explicitly in your summary to the user rather than only noting it in the
  report.
- New metrics get added to `run_eval.py` and this template together —
  don't let the report format drift out of sync with what the script emits.
