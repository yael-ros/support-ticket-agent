# Generation quality rubric (v1)

Used by `evaluation/llm_judge.py` to score a drafted response
(`agent/nodes/draft.py`'s output) against the ticket it's replying to and
the knowledge-base excerpts it was given. This is a softer, more holistic
signal than `agent/guardrails.py`'s deterministic pass/fail checks — the
guardrails catch specific failure modes (unauthorized promises, PII,
ungrounded claims); this rubric asks a model to judge overall quality the
way a support team lead reviewing a drafted reply would.

Three dimensions, each scored 1-5. The judge must also give a one-
sentence `rationale` per score — a bare number isn't reviewable.

## Helpfulness

Does the reply actually move the customer toward resolving their
problem?

- **1** — Doesn't address the customer's actual problem at all (wrong
  topic, generic non-answer).
- **2** — Related to the problem but gives no actionable next step.
- **3** — Gives some actionable guidance, but it's incomplete, generic,
  or leaves an obvious follow-up question unanswered.
- **4** — Directly addresses the problem with clear, actionable steps a
  customer could follow without further help.
- **5** — Fully resolves the problem, or gives a complete, unambiguous
  path to resolution, anticipating the obvious follow-up.

## Correctness

Is every factual claim in the reply actually supported by the retrieved
knowledge-base excerpts it was given? This dimension is specifically
about *this* draft against *this* retrieval context — a reply can be
"correct" in this sense and still be unhelpful (e.g. correctly reporting
that nothing relevant was found).

- **1** — Contains a claim that contradicts the retrieved excerpts, or is
  fabricated outright (no excerpt supports it and none was cited).
- **2** — Contains at least one claim not supported by any retrieved
  excerpt, presented as fact.
- **3** — Mostly accurate, but has one minor unsupported detail or
  imprecise restatement of what an excerpt actually says.
- **4** — Every claim is supported by a retrieved excerpt; only cosmetic
  room for a more precise restatement.
- **5** — Fully accurate — every factual claim is directly and correctly
  grounded in a retrieved excerpt, with no overstatement.

## Tone

Is this how a skilled, professional human support agent would write to
this customer?

- **1** — Rude, dismissive, or otherwise inappropriate for a support
  context.
- **2** — Curt or robotic in a way that would frustrate a customer, even
  if not overtly rude.
- **3** — Neutral and acceptable, but flat — neither warm nor
  off-putting.
- **4** — Professional, courteous, and appropriately empathetic given the
  ticket's tone/urgency.
- **5** — Professional, warm, and reassuring — exactly how a skilled
  human agent would write it for this specific ticket.

## Scoring notes

- Score against what the draft actually says, not what it *should* have
  said given a better retrieval — a low-quality retrieval producing a
  correctly-hedged "I don't have enough information, a human will follow
  up" reply should score well on correctness and helpfulness given that
  constraint, not be penalized for the retrieval's limits.
- These scores are a quality signal for the eval report
  (`eval/results/full_report.md`), not a routing input — `route.py`'s
  auto-send decision is based on classification confidence and the
  deterministic guardrails only (see `agent/nodes/route.py`), not this
  rubric.
