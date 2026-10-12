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

`data/grid/quran.db` has been identified as containing the Persian translation by Hussain Ansarian. The wording matches Tanzil's `fa.ansarian` translation, and Tanzil's official translation endpoint publishes the same 6236-ayah translation in the standard `sura|aya|translation` format. Tanzil's documentation states that every translation file has exactly 6236 lines, with one aya per line. [Tanzil translation-format documentation](https://tanzil.net/docs/adding_new_translations)

SIMORGH now contains a reproducible build script, `scripts/build_tanzil_quran_db.py`, which fetches the translation directly from `https://tanzil.net/trans/fa.ansarian` at build time and inserts the rows verbatim into SQLite without editorial rewriting. `scripts/verify_tanzil_quran_db.py` compares the stored rows against the live Tanzil source. The repository CI invokes this verifier. [build script](../scripts/build_tanzil_quran_db.py) and [verifier](../scripts/verify_tanzil_quran_db.py)

The direct Tanzil endpoint is therefore the authoritative source for rebuilding the SIMORGH copy. The existing database becomes `VERIFIED` as a source match only after the rebuild or verifier succeeds on that exact checked-in file. The current CI run exposed a verifier parsing bug before content comparison, so the source match is presently **[NOT VERIFIED]** despite the source identity being established. fileciteturn441114view0

### Rights boundary for `fa.ansarian`

Tanzil's general translation terms state that translations are provided for non-commercial purposes only; other use requires permission from the translator or publisher. Therefore identifying the exact Tanzil source does **not** by itself establish commercial redistribution rights for SIMORGH. [Tanzil translation terms](https://tanzil.net/trans/)

Tanzil's separate CC BY 3.0 license for the Quran text itself applies to Tanzil Quran text, not automatically to the third-party Persian translation. The Arabic Quran text terms permit verbatim distribution with attribution and prohibit changing the text. [Tanzil Quran Text License](https://tanzil.net/docs/Text_License)

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

## Database inventory and SHA-256 register (owner output, 2026-10-12)

This is the single inventory register for the database copies discussed in the paper review. A hash proves byte identity for the measured files; it does not establish authorship, source lineage, licence, permission, or redistribution rights. Paths labelled “inventory reference” are not legal or provenance approval. Duplicate copies are listed for traceability only and must **not** be deleted as part of this audit.

### Owner-measured local copies

| Logical asset / role | Inventory reference copy | SHA-256 | Identical copies observed in the same `sha256sum` output | Provenance / redistribution status |
|---|---|---|---|---|
| Persian poetry runtime DB (`persian_poetry.db`) | `SIMORGH_ROOT/data/poetry/persian_poetry.db` | `89299548823406c838857800c387492932ac456cb10a45af330e3ee81513079f` | `ARCHIVE_ROOT/SimorghCore/data/poetry/persian_poetry.db`; `PHONE_BACKUP_ROOT/simorgh_old_backup/data/persian_poetry.db` | Source/edition metadata not found in the inspected schema; redistribution rights `NOT_VERIFIED`. Runtime benchmark is not reproducible from a clean public clone until the exact permitted asset and hash are available. |
| Archived Quran DB (`quran.db`, multiple editions reported) | `ARCHIVE_ROOT/SimorghCore/data/poetry/quran.db` | `dc3f6a2abd83f9020526cc48be44b80fa886651afb715a546d8ad17a02b47fc4` | `PHONE_BACKUP_ROOT/simorgh_old_backup/data/quran.db` | Database-level source lineage/permissions not established by the inspected schema. Edition identifiers/names are metadata, not proof of acquisition lineage or redistribution permission. Do not assume this copy matches `data/grid/quran.db`. |

### Database assets tracked in the public repository tree

| Tracked path | SHA-256 | Evidence state | Required next verification |
|---|---|---|---|
| `data/grid/quran.db` | **NOT MEASURED** | Tanzil `fa.ansarian` is the recorded candidate source, but exact source-to-file match remains `NOT_VERIFIED`; the archived `quran.db` hash above is a different path and must not be substituted. | Run `sha256sum data/grid/quran.db` in the owner’s checkout and separately run the repository source verifier after its known parsing issue is fixed. Preserve the non-commercial restriction unless explicit permission covers the intended use. |
| `data/simorgh.db` | **NOT MEASURED** | Exact upstream source/edition, compilation rights and redistribution terms remain `NOT_VERIFIED`. | Run `sha256sum data/simorgh.db`; record a pinned source and reproduce the build before making any open-data claim. |
| `data/simorgh_full.db` | **NOT MEASURED** | Ganjoor is a candidate source for part of the data, but the exact assembled content and compilation/editorial-layer rights remain `NOT_VERIFIED`. | Run `sha256sum data/simorgh_full.db`; record an exact source snapshot, derivation manifest and rights basis. |

The owner output did not include SHA-256 values for the three tracked public-tree database paths. They intentionally remain `NOT MEASURED` in this record. Do not fill them by copying hashes from similarly named files in archives or backups.

### Copy policy

- Hash-identical copies are retained in the inventory as duplicate copies; this task performs no deletion or cleanup.
- No inference is made that a local runtime-only poetry database is present in the public tree. The inspected public tree did not contain the default `data/poetry/persian_poetry.db` path used by `app/knowledge/poetry_lookup.py`.
- “Publicly accessible source”, “open data”, “redistributable data”, and “reproducible public benchmark” are separate claims. Do not use the last three until the owner confirms provenance, exact files/hashes, permission/licence, and clean-clone availability.
