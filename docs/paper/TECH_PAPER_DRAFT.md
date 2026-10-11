# Provenance-first retrieval for Persian poetry attribution on commodity hardware  (DRAFT, anonymised for double-blind review)

> Optional target: SilkRoadNLP 2027, direct paper deadline 15 Dec 2026, with a strong thematic fit to Iranian-language NLP and technological sovereignty. This draft is a separate technical framing, not approved for submission: first confirm the national conference's overlapping-submission rules and complete the benchmark/data-rights gates. AbjadNLP is an alternative, not a second simultaneous submission. Double-blind formatting and an anonymised source mirror must be checked before any submission.

## Abstract
See `docs/paper/ABSTRACT.md` (English version), updated with the held-out numbers below.

## 1 Introduction
- Problem: a small local LLM is unreliable on Persian literary facts; cloud APIs are not always available or acceptable. [CITE: Persian LLM evaluation, low-resource NLP]
- Contribution (keep to what is evidenced): (1) a deterministic, provenance-first lookup for verse attribution over ~1.4M verses; (2) an abstention rule that avoids certifying a poet when a phrase is too common; (3) a reproducible evaluation protocol with dev/held-out samples, perturbations, chimeras and error analysis; (4) a comparison with the same LLM used alone.

## 2 Related work

Persian LLM evaluation has begun to include wider task and culture coverage. Abaskohi et al. (2024) benchmarked several LLMs on classic, reasoning and knowledge-based Persian tasks and contributed new reasoning datasets; Hosseinbeigi et al. (2025) introduced PeKA and PK-BETS for Persian knowledge, literature and culture. The proposed 40-item set here is much smaller and deliberately task-specific: it is intended to test a local pipeline and abstention on a frozen set, not to replace or compete with broad Persian benchmarks. Its measured results are still pending.

Raji et al. (2024) describe a machine-readable Persian literary corpus annotated for time period and style, while Shahnazari et al. (2025, preprint) study Persian poetry authorship recognition with a supervised model over a curated corpus. Those tasks are not directly comparable to SIMORGH's phrase-matching attribution path: the latter asks whether a known phrase can be matched to a stored record and declines to certify common or ambiguous phrases, rather than classifying arbitrary verses across poets.

Lewis et al. (2020) describe retrieval-augmented generation as a way to condition model outputs on explicit non-parametric memory. SIMORGH also retrieves local text, but the current implementation has two distinct behaviors: a deterministic route for certain verse-attribution requests, and ordinary retrieval that supplies context to the language model. This paper therefore reports the deterministic attribution task separately from the LLM-only versus LLM-with-context ablation.

The coverage/abstention trade-off is related to selective classification (Geifman and El-Yaniv, 2017). The current lookup reports empirical coverage, answered accuracy and candidate inclusion; it is not a calibrated risk-controlling selective classifier and offers no formal error guarantee.

## 3 System
- Historical test stack: local llama.cpp server (Gemma-3-4B QAT Q4_0), FastAPI and SQLite/FTS. Recorded test machine: Core i5-4460, about 7.7 GB RAM, no GPU. A single current throughput figure is omitted because historical run contexts differ; throughput in the new four-condition benchmark is NOT_MEASURED.
- Provenance boundary: the specific verse-attribution route in `app/knowledge/poetry_lookup.py` can return a database-backed answer without the LLM and marks that response `ai_generated=false`. Ordinary Quran/poetry/book retrieval generally contributes context to the model prompt, so final answers are not universally model-independent. The existing greeting guard blocks retrieval for small talk.
- Data: historical evidence reports a local poetry corpus with 1,406,919 verse records and poet IDs. The default `data/poetry/persian_poetry.db` path used by the attribution module was not present in the current public tree reviewed for this draft. Clean-clone availability, exact file/hash/source provenance and redistribution rights are NOT VERIFIED; do not describe the dataset as publicly reproducible until these gates are resolved.

## 4 Method: verse attribution
1. Normalise (ي→ی, ك→ک, strip diacritics); tokenise into words.
2. **Phrase stage:** FTS5 phrase query on up to 6 words, fetching k+1 = 9 rows. One poet among ≤ k hits and ≥ 4 words → *answer*; several poets → *ambiguous*; a **full window** (more than k hits) → *uncertain* even if all visible hits share one poet (defect found by held-out evaluation, §6.3).
3. **Fallback stage:** OR query over content words; *answer* only if lexical overlap ≥ 0.8, ≥ 4 words (repository version: ≥ 4 content words) and the top-3 hits agree on the poet; otherwise *uncertain* with candidate poets.
4. Statuses `ambiguous`/`uncertain` are shown to the user as "not sure; possibly: …".

## 5 Evaluation protocol
- Queries are derived from the database itself (EASY setting): measure retrieval and abstention, not accuracy on arbitrary user input.
- Variants: first 6 words; middle 4 words; one-letter perturbations (last letter dropped, middle letter dropped, adjacent swap); **chimera** verses (3 words of one verse + 3 words of another by a different poet) to measure false acceptance.
- Dev seed 7 (where defects were found and fixed) vs held-out seeds 11, 23, 37 (n = 300 each, pooled n = 900); 95% Wilson intervals; ground truth for a verse listed under several poets is the *set* of holders (refinement made after error analysis; strict counts are kept in the JSON output).

## 6 Results
### 6.1 Held-out (pooled n = 900)  — source: `docs/evidence/ATTRIBUTION_HELDOUT.md`
| Variant | Answered | Answered-accuracy | Abstained, poet among candidates |
|---|---|---|---|
| first 6 words (EASY) | 896/900 (99.6%) | 896/896 (CI 99.6–100) | 4/4 |
| middle 4 words | 864/900 (96.0%) | 864/864 (CI 99.6–100) | 34/36 |
| last letter dropped | 299/900 (33.2%) | 299/299 (CI 98.7–100) | 557/601 |
| middle letter dropped | 297/900 (33.0%) | 297/297 (CI 98.7–100) | 558/603 |
| adjacent swap | 303/900 (33.7%) | 303/303 (CI 98.7–100) | 560/597 |
| chimera accepted | 1/416 (0.2%, CI 0–1.3) | | |

### 6.2 LLM alone vs lookup (same verses, same 6-word query)
Gemma-3-4B QAT Q4_0, temperature 0; poet-name matching deliberately lenient toward the LLM. Held-out seeds 11, 23, 37 (n = 100 each).

| System | Correct | Abstained | Wrong |
|---|---|---|---|
| LLM alone (no retrieval) | 29/300 = 9.7% (95% CI 6.8–13.5) | 0 | 271 |
| Deterministic lookup | 299/299 of the 299 it answered (CI 98.7–100) | 1 | 0 |

Per seed the LLM got 7, 8 and 14 of 100 right; on the dev seed 7 it got 14. It never abstained in 400 queries. Source: `docs/evidence/EVAL_2026-10-05.md`.

### 6.3 Error analysis and a defect found by held-out evaluation
- First run: 1 wrong answer among 288 (middle-4-words): «و روشن دل و» (Nizami) attributed to Ferdowsi because the first 8 hits of a stock phrase were all Ferdowsi. Fix: window-full → *uncertain*. Held-out result after the fix: 864/864.
- Typo variants: the only "errors" were one verse listed in the database under two poets (a quotation).
- The only accepted chimera returned one of its two source poets.

## 7 Limitations
Single machine; queries derived from the database; correctness bounded by the database's attributions; ≈ 1/3 coverage under one-letter corruption (abstains rather than guesses); no human evaluation; no user study; LLM QA pilot (n = 10) is too small for claims.

## 8 Reproducibility

The held-out poetry results in §6 refer to the previously recorded reports in `docs/evidence/ATTRIBUTION_HELDOUT.md` and `docs/evidence/EVAL_2026-10-05.md`. The exact poetry database path used by `app/knowledge/poetry_lookup.py` is absent from the public tree inspected for this draft, so a clean-clone reproduction has **not** been demonstrated. The command below is only applicable after the exact data asset has been obtained through a documented and permitted route; success from a fresh checkout is currently NOT VERIFIED.

```bash
python eval/run_eval.py --no-llm --attr-n 300 --seed 11
python eval/finalize_evidence.py
```

The newer 40-item benchmark in `eval/questions_paper_v1.json` remains PREPARED_NOT_RUN. It must first pass the Quran and poetry gold-reference audit; four timestamped model/retrieval condition JSON files, model/data SHA-256 values, latency, tokens/s, RSS and per-item outputs are required before reporting new numbers.

## Ethics

The poetry corpus and Quran translation have unresolved redistribution/provenance questions recorded in `docs/paper/B2_DATA_PROVENANCE_GATE.md`. Do not redistribute the source databases or claim a public, clean-clone reproduction until these rights and path checks are resolved. No human participants or actual municipal records were part of the historical poetry benchmark.

## References (located; full-text reading and venue formatting still required before submission)

- Abaskohi, A., Baruni, S., Masoudi, M., Abbasi, N., Babalou, M. H., Edalat, A., Kamahi, S., Mahdizadeh Sani, S., Naghavian, N., Namazifard, D., Sadeghi, P., and Yaghoobzadeh, Y. (2024). “Benchmarking Large Language Models for Persian: A Preliminary Study Focusing on ChatGPT.” *LREC-COLING 2024*, 2189–2203. https://aclanthology.org/2024.lrec-main.197/
- Geifman, Y., and El-Yaniv, R. (2017). “Selective Classification for Deep Neural Networks.” *NeurIPS 2017*, 4878–4887. https://arxiv.org/abs/1705.08500
- Hosseinbeigi, S. B., Rohani, B., Masoudi, M., Shamsfard, M., Saaberi, Z., Karimi Manesh, M., and Abbasi, M. A. (2025). “Advancing Persian LLM Evaluation.” *Findings of NAACL 2025*, 2711–2727. https://doi.org/10.18653/v1/2025.findings-naacl.147
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., and Kiela, D. (2020). “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.” *NeurIPS 2020*. https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
- Raji, S., Alikhani, M., de Melo, G., and Stone, M. (2024). “A corpus of Persian literary text.” *Language Resources and Evaluation*, 58, 409–425. https://doi.org/10.1007/s10579-023-09689-6
- Shahnazari, K., Keshtparvar, M., and Ayyoubzadeh, S. M. (2025). “PARSI: Persian Authorship Recognition via Stylometric Integration.” arXiv:2506.21840 (preprint). https://arxiv.org/abs/2506.21840
