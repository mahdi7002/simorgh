# Ganjoor-backed poetry rebuild

This document defines the recovery path for SIMORGH poetry data. The previous
attempt to repair 215 historical rows individually is no longer the primary path:
the poetry layer can instead be rebuilt from a pinned Ganjoor snapshot.

## Source snapshot

- Repository: `https://github.com/ganjoor/ganjoor-data`
- Pinned source commit: `a64968e78425b2e8c7904fbdf5289fba8251a757`
- Source generation timestamp: `2026-09-12T12:47:59.2264145Z`
- Source snapshot: 240 poets / 135319 poems

The pinned commit is intentional. Do not rebuild a release candidate from a
moving `main` URL. Ganjoor's API documents a static file layout and supports
commit-pinned snapshots for reproducibility.

## Why the individual-row path was retired

The current canonical SQLite database has no `poems_quarantine` table. The
historical quarantine is stored only in the ignored local file:

```text
data/quarantined_poems_backup.json
```

Git commit `c21ea7646215485c53768976943b4fc1934f3cbf` records the historical
operation as quarantining **215 corrupted poem rows** while retaining **2274
verified-clean poems** in the 31 MB canonical database. The backup file itself
is deliberately ignored and is not part of the public repository.

Several backup rows have generic titles such as `مجموعه اشعار` and reasons such
as `concatenated-multi-poem (len > 3000)`. Treating these as ordinary one-to-one
poet/title matches is therefore unreliable.

## Primary recovery path: full poetry-layer rebuild

Use `scripts/rebuild_poems_from_ganjoor.py` to construct a fresh staging database
from the pinned Ganjoor snapshot. The script:

1. Fetches or reuses a local checkout of the exact Ganjoor commit.
2. Reads `manifest.json` as the source of truth for poets and corpus counts.
3. Walks poem JSON files under `poets/`, excluding poet and category descriptor files.
4. Reconstructs text from ordered `Verses`, with `Sections.PlainText` as fallback.
5. Preserves the existing SIMORGH four-column `poems` contract:
   `id, poet, title, text, source`.
6. Deduplicates identical `(poet, title, text)` rows.
7. Applies the existing 3000-character safety boundary by default.
8. Copies the current canonical DB to staging first, preserving all non-poetry tables.
9. Recreates the `poems_fts` table from the existing SQLite definition when one
   exists, then rebuilds its index.
10. Runs `PRAGMA integrity_check` before declaring the staging DB valid.
11. Leaves the canonical DB untouched unless `--apply` is explicitly supplied.
12. When applying, creates a timestamped pre-rebuild backup and replaces the DB
   atomically.

The builder does not silently alter the canonical database. The explicit
`--apply` flag is the human authorization boundary.

## Build staging database

```bash
cd ~/simorgh
python3 scripts/rebuild_poems_from_ganjoor.py \
  --db data/simorgh_full.db \
  --output rebuild_staging/ganjoor_simorgh_full.db \
  --source-dir rebuild_staging/ganjoor-data
```

The source checkout and resulting DB remain under `rebuild_staging/`, which is
already ignored by Git.

## Apply the rebuilt poetry layer

After inspecting the printed statistics and verifying that the staging DB opens
correctly:

```bash
python3 scripts/rebuild_poems_from_ganjoor.py \
  --db data/simorgh_full.db \
  --output rebuild_staging/ganjoor_simorgh_full.db \
  --source-dir rebuild_staging/ganjoor-data \
  --apply
```

The command prints the backup path before replacing `data/simorgh_full.db`.
Never delete that backup until post-rebuild tests pass.

## About the 3000-character boundary

The default is `--max-chars 3000` to preserve the existing SIMORGH poetry-data
contract used during the previous cleanup. Set `--max-chars 0` only when the
application contract has been deliberately changed to support unrestricted poem
lengths and the relevant tests have been updated.

A full Ganjoor rebuild is intentionally different from the old 215-row backup
repair: a long poem is not evidence of corruption merely because an old local
row exceeded 3000 characters. It is skipped by the default staging policy and is
reported in build statistics for a deliberate policy decision.

## Source and rights boundary

The pinned Ganjoor README and API document the repository as a public,
git-tracked export of published poetry content and state that user-account-linked
data such as comments, bookmarks, reading history, and edit history are not
included. The API defines the exact poem file layout and JSON structure.

The `ganjoor-data` repository does **not** provide a `LICENSE` file in the pinned
snapshot. Therefore SIMORGH must not manufacture a license for the compilation,
metadata, formatting, or other editorial layers.

For classical authors, the underlying original literary works are expected to be
outside normal copyright terms because of their age, but this remains a
**public-domain candidate status** rather than a universal legal conclusion for
every shipped record. Modern translations, critical editions, annotations,
corrections, summaries, and other contributed editorial material require separate
assessment.

Accordingly, keep the Ganjoor-derived compilation/editorial layer
**NOT_VERIFIED** in `compliance/ASSET_RIGHTS.csv` until the human maintainer has
accepted a concrete redistribution basis and attribution requirements.

## Release gate

The rebuild script can create or apply a database, but it must not change the
rights ledger automatically. A successful technical rebuild does not imply legal
clearance.

Do not commit:

```text
rebuild_staging/
data/quarantined_poems_backup.json
*.pre_ganjoor_*.bak
```

Those are local recovery/build artifacts.

## Verification after apply

Run at minimum:

```bash
cd ~/simorgh
sqlite3 data/simorgh_full.db "PRAGMA integrity_check;"
sqlite3 data/simorgh_full.db "SELECT COUNT(*) FROM poems;"
sqlite3 data/simorgh_full.db ".schema poems"
python3 -m pytest -q
```

Then run the repository compliance and runtime audits before treating the rebuilt
database as release-ready.
