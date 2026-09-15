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

### Quran text

Tanzil publishes Quran text under Creative Commons Attribution 3.0 and explicitly permits verbatim copying and distribution, with source attribution and a requirement not to change the text. This is a usable rights basis for a Tanzil-sourced verbatim Quran text, but SIMORGH has not yet established that `data/grid/quran.db` is actually derived from Tanzil or that its stored content is the exact Tanzil text covered by those terms.

Quran translations are a separate rights question. Tanzil states that its listed translations are for non-commercial use unless permission is obtained from the translator or publisher. No translation should therefore be classified as freely redistributable without identifying the exact translation and its license.

Quran Foundation's current developer terms are also not a suitable basis for shipping a raw local copy of API content: the terms restrict redistribution of QF Content and require a separate written commercial license for redistribution of QF Content or raw API data.

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

## Release rule

Until those facts are established, `compliance/ASSET_RIGHTS.csv` must stay `NOT_VERIFIED` for the affected assets. A successful technical rebuild, SQLite integrity check, SBOM, CI run, or public-surface audit does not constitute rights clearance.

## References

- Ganjoor data repository: https://github.com/ganjoor/ganjoor-data
- Tanzil text license: https://tanzil.net/docs/Text_License
- Tanzil download/terms: https://tanzil.net/download/
- Tanzil translations terms: https://tanzil.net/trans/
- Quran Foundation Developer Terms: https://api-docs.quran.com/legal/developer-terms/
