## Run: 2026-08-18T09:42:40+00:00 — 6f5e54a

n = 37 succeeded (3 failed, 40 attempted)

Failures:
- ticket-010321: LLMCallError: Model output failed schema validation: 1 validation error for DraftResponse
  Invalid JSON: EOF while parsing a string at line 1 column 1797 [type=json_invalid, input_value='{"text":"Thank you for r...of me confirming that a', input_type=str]
    For further information visit https://errors.pydantic.dev/2.10/v/json_invalid
- ticket-010478: LLMCallError: Model did not return a parseable JudgeScore. stop_reason='max_tokens', content=[ThinkingBlock(signature='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', thinking='', type='thinking')]
- ticket-003823: LLMCallError: Model output failed schema validation: 1 validation error for DraftResponse
  Invalid JSON: EOF while parsing a string at line 1 column 5100 [type=json_invalid, input_value='{"text":"Thank you for r... caches the entire work', input_type=str]
    For further information visit https://errors.pydantic.dev/2.10/v/json_invalid

### Classification
- Category accuracy: 0.622 (n=37)
- Category F1 (macro): 0.556
- Urgency accuracy: 0.568
- Urgency F1 (macro): 0.566

### Retrieval
- Precision@3: 0.333
- Recall@5: 1.000

### Generation (LLM-as-judge, rubric v1)
- Helpfulness: 3.54/5 (avg)
- Correctness: 4.81/5 (avg)
- Tone: 4.03/5 (avg)

### Operations
- Auto-send rate at threshold=0.75: 0.324
- Avg latency per ticket: 12.92 s
- Est. cost per ticket: $0.00106 (illustrative rate, not verified live pricing — see run_eval.py)
- Total tokens across run: 283634 in / 26760 out

## Run: 2026-08-18T09:57:21+00:00 — 8f0e551

n = 40 succeeded (0 failed, 40 attempted)

### Classification
- Category accuracy: 0.650 (n=40)
- Category F1 (macro): 0.562
- Urgency accuracy: 0.600
- Urgency F1 (macro): 0.612

### Retrieval
- Precision@3: 0.333
- Recall@5: 1.000

### Generation (LLM-as-judge, rubric v1)
- Helpfulness: 3.75/5 (avg)
- Correctness: 4.83/5 (avg)
- Tone: 4.17/5 (avg)

### Operations
- Auto-send rate at threshold=0.75: 0.275
- Avg latency per ticket: 12.69 s
- Est. cost per ticket: $0.00102 (illustrative rate, not verified live pricing — see run_eval.py)
- Total tokens across run: 299758 in / 27494 out

## Run: 2026-08-18T10:16:56+00:00 — 72eb1ea

n = 40 succeeded (0 failed, 40 attempted)

### Classification
- Category accuracy: 0.675 (n=40)
- Category F1 (macro): 0.577
- Urgency accuracy: 0.625
- Urgency F1 (macro): 0.633

### Retrieval
- Precision@3: 0.333
- Recall@5: 1.000

### Generation (LLM-as-judge, rubric v1)
- Helpfulness: 3.80/5 (avg)
- Correctness: 4.90/5 (avg)
- Tone: 4.15/5 (avg)

### Operations
- Auto-send rate at threshold=0.75: 0.250
- Avg latency per ticket: 12.68 s
- Est. cost per ticket: $0.02029 (real, verified pricing as of 2026-08-18 — see run_eval.py for the source and expiry of any introductory rates)
- Total tokens across run: 298572 in / 27375 out

