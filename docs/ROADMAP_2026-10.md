# Roadmap to the national conference / نقشهٔ راه تا همایش ملی

Updated 2026-10-12. External deadline listed by the conference directory: **30 Dey 1405 / 20 Jan 2027**. Internal target: **13 Jan 2027**.

## 1. Evidence boundary today

| Work | Current status | What this does not prove |
|---|---|---|
| Existing evaluation harness and held-out poetry-attribution results | Existing code and historical evidence files are in the public repository | They do not satisfy the new 40-item, two-model, four-condition benchmark |
| Persian paper and abstract drafts | Drafts exist in `docs/paper/` | They are not submission-ready; references, data-rights gate, venue template, author block and fresh benchmark outputs remain open |
| Fixed 40-item paper benchmark | Prepared on branch `paper/b2-benchmark-2026-10-12` | Not yet run; Quran gold phrases and poetry labels must be audited against the exact local databases first |
| Clean-clone data reproducibility | **Blocked / NOT VERIFIED** | Current public tree lacks the default `data/poetry/persian_poetry.db` path expected by `app/knowledge/poetry_lookup.py`; the corresponding evidence file is also not tracked |
| Quran data source and rights | Source identified as Tanzil `fa.ansarian`; non-commercial terms are recorded | Exact database match and redistribution permission remain NOT VERIFIED |
| New benchmark with Gemma and Qwen, each with and without retrieval | **Not measured** | No model-score, latency, token-rate or RSS numbers may be reported until the runs produce raw JSON |
| Five-minute offline showcase | Planned | Do not claim the whole scenario works offline until a timed test is run on the actual machine |

## 2. Critical path

| Target | Work | Completion evidence |
|---|---|---|
| 12 Oct onward, max ~2 hours total | Finish only the bounded Mother audit; if criteria do not pass, leave the old database untouched. Then freeze Mother. | Actual `mother_finish.sh` output, read-only diagnostics, weekly unit test and targeted pytest output. Never weaken the deletion criteria. |
| By 16 Oct (optional, only if demo works) | Submit the DHNB 2027 poster/demo abstract (250–500 words) or works-in-progress abstract (500–1,000 words), in English. | Actual five-minute test, data-display permission check, abstract word count and submission receipt. Do not let this delay the benchmark. |
| By 24 Oct | Test and stabilize one five-minute offline Persian scenario on the actual target machine. Fix only failures on that path. | Timestamped run note and backup recording; no number without command or observation evidence. |
| By 26 Oct | Decide whether to pursue a separate technical workshop paper. | One explicit choice after checking AbjadNLP and SilkRoadNLP policies. Do not submit the same or substantially overlapping paper to both. |
| By 21 Nov | Audit and run the fixed benchmark: 40 items, 4 categories, Gemma/Qwen, retrieval off/on. | Four timestamped JSON files; model and database SHA-256; temperature, latency, tokens/s, RSS; raw per-item outputs and error analysis. The dataset and references remain frozen during scored runs. |
| By 21 Nov | Optional, distinct DH2027 poster/demo proposal. | 500–750-word English proposal with references actually read; working demo and legal clearance for every displayed dataset. Do not let this block benchmark work. |
| By 5 Dec | Reproduce from a fresh checkout without deleting or overwriting the owner's active work. | Exact checkout instructions, tests, database hashes, model hashes and complete setup log. If the poetry database is unavailable or licensing is unresolved, document the blocker rather than claim full reproduction. |
| By 19 Dec | Revise the Persian abstract and main paper using measured results only; cite sources read by the author. | No placeholders; all tables trace to raw JSON; limitations and data-rights boundary explicit. |
| By 9 Jan | Final edit, template verification, originality/policy check and submission package. | Checklist complete; no unmeasured numbers; no unverified license claims. |
| By 13 Jan | Send the national paper, leaving the listed 30 Dey deadline as contingency. | Submission receipt and exact uploaded PDF/archive. |

## 3. Writing principles

- Primary framing: infrastructure, technology and technological independence; SIMORGH is a case study, not a product pitch.
- Do not state that the system is fully reproducible from a clean clone until the exact data path and licensing gap are resolved.
- Preserve older attribution results with their easy-setting caveat. New benchmark results must be reported separately and must not replace them without an explicit explanation.
- Report the one-machine, two-model scope; the small sample; any mismatches in source retrieval; and every relevant abstention/failure.
- The charter (`docs/CHARTER.md`) can appear as a short governance design section, not as evidence of effectiveness.
- Policy recommendations must be traceable to measured results and clearly identified as recommendations, not experimental findings.

## 4. Freeze list through paper submission

No Hodhod rebrand, new Mother subsystems, agent expansion, new city display modules, new mesh layers, robotics/ESP32 work, or unrelated feature development. Only fix issues necessary to make the frozen demo/evaluation path work and to make the paper reproducible.

## 5. After the national submission

First assemble a source-backed tracker of additional calls/showcases using `docs/CONFERENCES.md`. Keep separate framings for policy research, reproducible Persian NLP and digital-cultural-heritage demonstration; verify overlap and archiving rules before any submission.
