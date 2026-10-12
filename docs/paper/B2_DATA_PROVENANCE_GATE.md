# Data provenance gate for the SIMORGH paper

Reviewed against the current public repository tree and compliance records on 2026-10-12. This is a source review, not a database run or legal opinion.

## Quran translation

- Tracked asset: `data/grid/quran.db`.
- Recorded source in `compliance/ASSET_RIGHTS.csv`: `https://tanzil.net/trans/fa.ansarian`.
- Recorded translator / rights holder: Hussain Ansarian.
- Recorded condition: non-commercial use only unless permission from the translator or publisher is obtained.
- Exact database/source match and redistribution clearance: `NOT_VERIFIED`.
- `docs/ASSET_PROVENANCE.md` records that the verifier encountered a parsing defect before content comparison. SQLite integrity alone would not establish text rights or exact match.

## Poetry corpus

- `docs/ASSET_PROVENANCE.md` describes a pinned `ganjoor/ganjoor-data` source but says the corpus/compilation/editorial-layer license is not established.
- `compliance/ASSET_RIGHTS.csv` leaves source, license and redistribution rights for `data/simorgh_full.db` as `[NOT VERIFIED]`.
- `app/knowledge/poetry_lookup.py` defaults to `data/poetry/persian_poetry.db`; neither that path nor `data/poetry/EVIDENCE.md` appeared in the tracked public tree reviewed here. A clean clone may therefore skip poetry attribution unless the database is obtained through another documented route.
- Do not claim clean-clone reproducibility until the exact file path, schema, hash, pinned source snapshot and legal redistribution basis are documented and verified.

## Release gate

1. Run database checks on the actual local files and retain the complete output.
2. Audit every benchmark Quran reference against the exact local translation before scoring it as gold.
3. Audit poetry labels against the exact corpus before making corpus-relative accuracy claims.
4. Record SHA-256 for every input database and model.
5. Keep data permissions separate from the repository's MIT software license.
6. Retain `[NOT VERIFIED]` where any source, match or license remains unresolved.

This note alone does not upgrade any item to `VERIFIED`.
