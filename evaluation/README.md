# SIMORGH Evaluation

This directory defines a small, dependency-free evaluation boundary for knowledge tools.

## Case schema

Each JSONL row contains a query and optional expectations:

```json
{"id": 1, "q": "این بیت از کیست؟ چو بشنید پیچان شد افراسیاب", "poet": "فردوسی", "status": "answer"}
{"id": 2, "q": "ماه و ابر و کوه و باد از کیست؟", "status": "uncertain"}
```

`must_not_answer: true` can be used when accepting an answer would count as a false positive.

## Running

The evaluator accepts any local Python callable with `module:function` syntax:

```bash
python -m evaluation.knowledge_eval \
  --cases /path/to/poetry.jsonl \
  --callable app.knowledge.poetry_lookup:lookup \
  --output results/poetry.json
```

The callable receives one query string. It may return the structured result used by the tool or a list of result dictionaries.

## Metrics

The report records:

- coverage of known cases
- accuracy among answered known cases
- false-positive count/rate
- abstention count
- total and mean latency

For SIMORGH, false positives must remain visible rather than being hidden by a single aggregate accuracy number.
