# SIMORGH Asset Provenance Review Baseline

This document records the current evidence boundary for shipped data assets. It is a provenance and compliance engineering record, not legal advice.

## Rule

A source being public, old, searchable, or technically importable is not by itself proof that SIMORGH may redistribute the resulting asset. `compliance/ASSET_RIGHTS.csv` must remain `NOT_VERIFIED` until the exact shipped material has an identified source, rights basis, attribution requirements, and redistribution conditions.

The root SIMORGH MIT license covers SIMORGH software. It does not automatically license embedded datasets, translations, audio, or third-party editorial material.

## Current shipped paths

The current `main` tree contains these `data/` assets:

- `data/cultural_data.json`
- `data/grid/quran.db`
- `data/reflection_proposals/architecture_issues.json`
- `data/simorgh.db`
- `data/simorgh_full.db`

The previous ledger entries for top-level `quran/` and `music/` did not correspond to tracked paths in the current tree and have therefore been removed from the ledger. They must not be treated as shipped assets unless they are actually added to the repository.

## Evidence currently established

### Ganjoor

SIMORGH has a separate draft rebuild path for a pinned `ganjoor/ganjoor-data` snapshot. The pinned repository describes itself as a public, git-tracked export of Ganjoor poetry content and currently tracks 240 poets / 135,319 poems. The pinned snapshot does not declare an open-source data license. Therefore the underlying classical poems may be public-domain candidates because of their age, but the Ganjoor compilation, metadata, formatting, summaries, and other editorial layers require separate assessment before redistribution.

Do not mark the Ganjoor-derived portion of `data/simorgh_full.db` `VERIFIED` merely because individual historical works are old enough to be public domain.

### Quran translation: Tanzil `fa.ansarian`

`data/grid/quran.db` has been identified as containing the Persian translation by Hussain Ansarian. The wording matches Tanzil's `fa.ansarian` translation, and Tanzil's official translation endpoint publishes the same 6236-ayah translation in the standard `sura|aya|translation` format. Tanzil's documentation states that every translation file has exactly 6236 lines, with one aya per line. citeturn322118search0turn322118search2

SIMORGH now contains a reproducible build script, `scripts/build_tanzil_quran_db.py`, which fetches the translation directly from `https://tanzil.net/trans/fa.ansarian` at build time and inserts the rows verbatim into SQLite without editorial rewriting. `scripts/verify_tanzil_quran_db.py` compares the stored rows against the live Tanzil source. The repository CI invokes this verifier. fileciteturn185file0

The direct Tanzil endpoint is therefore the authoritative source for rebuilding the SIMORGH copy. The existing database becomes `VERIFIED` as a source match only after the rebuild or verifier succeeds on that exact checked-in file. The current CI run exposed a verifier parsing bug before content comparison, so the source match is presently **[NOT VERIFIED]** despite the source identity being established. fileciteturn441114view0

### Rights boundary for `fa.ansarian`

Tanzil's general translation terms state that translations are provided for non-commercial purposes only; other use requires permission from the translator or publisher. Therefore identifying the exact Tanzil source does **not** by itself establish commercial redistribution rights for SIMORGH. citeturn322118search2

Tanzil's separate CC BY 3.0 license for the Quran text itself applies to Tanzil Quran text, not automatically to the third-party Persian translation. The Arabic Quran text terms permit verbatim distribution with attribution and prohibit changing the text. citeturn322118search1turn322118search11

## What remains to be proven

For each shipped database or JSON asset, a human maintainer must establish:

1. the exact source or source record;
2. the exact content type and edition;
3. rights holder or public-domain basis where applicable;
4. applicable license or permission;
5. database/compilation rights where material;
6. translation rights where applicable;
7. required attribution and notices;
8. redistribution and commercial-use restrictions;
9. a reproducible source-to-shipped-asset mapping.

For `data/grid/quran.db`, the remaining human/legal item is permission or a license basis covering the embedded Ansarian translation for the intended redistribution model. Do not infer that permission from the fact that Tanzil hosts a downloadable copy.

## Release rule

Until those facts are established, `compliance/ASSET_RIGHTS.csv` must stay `NOT_VERIFIED` for the affected assets. A successful technical rebuild, SQLite integrity check, SBOM, CI run, or public-surface audit does not constitute rights clearance.

## References

- Tanzil Quran translations: https://tanzil.net/trans/
- Tanzil Hussain Ansarian translation: https://tanzil.net/trans/fa.ansarian
- Tanzil translation format: https://tanzil.net/docs/adding_new_translations
- Tanzil text license: https://tanzil.net/docs/Text_License
- Tanzil download/terms: https://tanzil.net/download/
- Tanzil translation resources: https://tanzil.net/docs/translations_resources
- Ganjoor data repository: https://github.com/ganjoor/ganjoor-data
- Quran Foundation Developer Terms: https://api-docs.quran.com/legal/developer-terms/
