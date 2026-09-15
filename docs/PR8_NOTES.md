# PR #8 validation notes

Local validation for head `610a701`:

- `pytest -q`: 49 passed
- `python3 -m compileall -q core scripts tests`: passed
- `git diff --check`: passed
- SQLite `PRAGMA integrity_check`: `ok`
- `poems`: 135319
- `poems_fts`: 135319
- pinned Ganjoor verifier: PASS
- `missing_or_mismatched`: 0
- `orphan_db_rows`: 0
- `duplicate_source_rows`: 0

The canonical `data/simorgh_full.db` is intentionally local and uncommitted because the PR does not publish the 375MB binary database.

The upstream Ganjoor dataset license remains `NOT VERIFIED`; provenance and redistribution rights are tracked separately.
