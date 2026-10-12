# Persian paper benchmark v1: execution protocol

Status: **prepared, not run** (2026-10-12). This is an experiment plan, not evidence of model performance.

## Fixed design

Dataset for scoring: `eval/questions_paper_v2.json` (corrected pre-run version). The earlier `eval/questions_paper_v1.json` is retained as history, but `poetry-01` uses a disputed common wording (`یک پیکرند`) and must not be used for scored runs. Version v2 changes it to `یکدیگرند` before any model output was inspected. The set contains 40 items, 10 per category:
- `poetry_attribution`: identify the poet;
- `source_qa`: answer a question tied to a Quran verse reference;
- `abstain`: questions designed to lack an answer in the available local source set;
- `classify`: label citizen reports with exactly one permitted class.

Temperature is zero, and the fixed seed is sent in each chat-completion request (default `--seed 7`; pass the same explicit `--seed 7` in all four runs). The seed also controls the local historical-sampling sections. Do not edit prompts after seeing model outputs. If the pre-run reference audit finds an incorrect gold answer, document the issue and correct it before the first scored run, with a new dataset version.

## Required pre-run audit

The ten Quran references are source pointers, not proof that the exact local translation has been checked. Match each reference against `data/grid/quran.db` and confirm the expected phrase in the exact local translation. Audit the ten poetry labels against the exact corpus before reporting corpus-relative results.

Ordinary QA uses literal expected-substring scoring, not semantic judging. Classification requires an exact normalized label. Abstention scoring checks for configured phrases, so inspect raw answers for false positives.

## Four-condition matrix

Run the same 40 prompts in `eval/questions_paper_v2.json` in all four conditions:
1. Gemma 3 4B QAT Q4_0, retrieval off;
2. Gemma 3 4B QAT Q4_0, retrieval on;
3. Qwen2.5 1.5B Instruct Q4_K_M, retrieval off;
4. Qwen2.5 1.5B Instruct Q4_K_M, retrieval on.

The `--retrieval` condition uses the local retrieval hint policy and existing Quran, poetry and book-search functions. It is an ablation of model-plus-context versus model-alone; it does not assume that each question receives relevant evidence. Per-run JSON records whether context was added, source-row counts, errors, each answer, accuracy per category, latency and tokens/s.

The deterministic verse-attribution route is separately evaluated by the existing attribution and LLM-baseline sections. It should not be conflated with the LLM-plus-context ablation.

Model SHA-256 and sampled model-server peak RSS must be recorded. If the exact model path or server PID is not passed, the result explicitly says `NOT_MEASURED`. The raw JSON for every run is the evidence; the Markdown summary alone is insufficient.

## Safe execution order

1. Inspect `git status --short`. Do not switch branches over uncommitted work; do not stash, reset, clean or discard changes.
2. Fetch and switch to branch `paper/b2-benchmark-2026-10-12` only when the working tree is clean. Do not merge it into `main` until tests and data-reference audit pass.
3. Run `git lfs pull` only if online and approved, then run:
   `python -m pytest -q tests/test_paper_benchmark.py tests/test_eval_harness.py tests/test_poetry_lookup.py --tb=short`
4. Run `python scripts/check_poetry_db.py data/simorgh_full.db data/grid/quran.db` and preserve the full output.
5. Run `python scripts/verify_tanzil_quran_db.py --db data/grid/quran.db` and preserve its exact output. If it fails, report the failure; do not call the data match verified.
6. Locate the actual Gemma and Qwen GGUF files and the real PIDs serving ports 8080 and 8081. Check the server's reported model before using these port mappings.
7. For each endpoint, run `eval/run_eval.py --questions eval/questions_paper_v1.json --url http://127.0.0.1:PORT/v1/chat/completions --baseline-n 0 --model-file ACTUAL_MODEL_PATH --server-pid ACTUAL_PID`; repeat that exact command with `--retrieval` for the second condition. Replace PORT, model path and PID only with values printed by the local machine.

The four runs may take time because each evaluates all 40 items. Each command writes a timestamped JSON in `eval/results/`; retain all four files. If a server/model mapping, database, SHA, RSS or retrieval source is missing, write `NOT_MEASURED` or the exact failure rather than inventing a number.

## Interpretation limits

- Verify source references before treating them as correct gold answers.
- Ten abstention cases do not prove general hallucination resistance.
- Ten classification cases provide only a small, task-specific estimate.
- Poetry prompts are curated rather than generated from the evaluation database, but their gold labels still need a corpus audit.
- The study compares two models on one machine, not a broad population of hardware or models.
- Report the model versions/hashes, source database hashes, software commit, hardware, all four conditions, category-level results, raw errors and the limitations together.


## Pre-run correction record (2026-10-12)

A source check against a text of Golestan showed that the commonly quoted first Saadi line is normally rendered "بنی‌آدم اعضای یکدیگرند". As the first draft used the disputed "یک پیکرند" wording while claiming a verse-level source, scoring was blocked and the correction was versioned in `questions_paper_v2.json` before any model outputs were inspected. The v1 file is retained rather than overwritten. The local poetry corpus audit is still required, and model scores must not be reported unless the exact local corpus can substantiate all poetry gold labels.

The 30-pair model-free normalization fixture is `eval/normalization_pairs_v2.json`; its script prints the fixture SHA-256 before making the first lookup. Pair invariance, no-hit rates, and data correctness are distinct metrics.
