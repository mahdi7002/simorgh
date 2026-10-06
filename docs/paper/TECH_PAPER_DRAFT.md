# Provenance-first retrieval for Persian poetry attribution on commodity hardware  (DRAFT, anonymised for double-blind review)

> Target: AbjadNLP 2027 (deadline 15 Dec 2026). Verify page limit/format on the workshop page. Replace the repository link with an anonymised mirror before submission. **No citations are filled in**: every `[CITE]` must be added by the author after reading the sources; do not cite from memory.

## Abstract
See `docs/paper/ABSTRACT.md` (English version), updated with the held-out numbers below.

## 1 Introduction
- Problem: a small local LLM is unreliable on Persian literary facts; cloud APIs are not always available or acceptable. [CITE: Persian LLM evaluation, low-resource NLP]
- Contribution (keep to what is evidenced): (1) a deterministic, provenance-first lookup for verse attribution over ~1.4M verses; (2) an abstention rule that avoids certifying a poet when a phrase is too common; (3) a reproducible evaluation protocol with dev/held-out samples, perturbations, chimeras and error analysis; (4) a comparison with the same LLM used alone.

## 2 Related work
Topics to cover (add sources): Persian poetry corpora and attribution; retrieval-augmented generation; selective prediction / abstention; evaluation of small quantised LLMs. [CITE ×N]

## 3 System
- Offline stack: llama.cpp server (Gemma-3-4B QAT Q4_0), FastAPI service, SQLite FTS5 databases. Hardware: Core i5-4460, 7.7 GB RAM, no GPU, ≈10 tokens/s generation.
- Provenance: answers from the database are returned without the LLM and flagged `ai_generated=false`; greetings never trigger retrieval.
- Data: `persian_poetry.db` (1,406,919 verses with poet ids; FTS5 index), distributed as a hash-checked Git LFS object.

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
**To be filled from `python eval/run_eval.py` section F** (do not write numbers here until the run exists).

### 6.3 Error analysis and a defect found by held-out evaluation
- First run: 1 wrong answer among 288 (middle-4-words): «و روشن دل و» (Nizami) attributed to Ferdowsi because the first 8 hits of a stock phrase were all Ferdowsi. Fix: window-full → *uncertain*. Held-out result after the fix: 864/864.
- Typo variants: the only "errors" were one verse listed in the database under two poets (a quotation).
- The only accepted chimera returned one of its two source poets.

## 7 Limitations
Single machine; queries derived from the database; correctness bounded by the database's attributions; ≈ 1/3 coverage under one-letter corruption (abstains rather than guesses); no human evaluation; no user study; LLM QA pilot (n = 10) is too small for claims.

## 8 Reproducibility
`git lfs pull && python eval/run_eval.py && python eval/finalize_evidence.py` regenerates every number in §6.

## Ethics
Poetry corpus provenance and licensing must be stated before submission (see `docs/ASSET_PROVENANCE.md`).
