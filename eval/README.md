# eval/

One command, reproducible numbers:

```bash
python eval/run_eval.py            # offline sections + LLM section if llama-server is up
python eval/run_eval.py --no-llm   # offline only
python eval/run_eval.py --questions path/to/your_questions.json
```

Writes `eval/results/<timestamp>.json` (full detail) and `eval/RESULTS.md` (latest table).
Question format: see `eval/questions.json` (`qa` / `abstain` / `classify`, matched by `expected_any`).
Quote only numbers produced by this script, with their *Setting* column and item counts.
