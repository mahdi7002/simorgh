# Ganjoor-backed poetry rebuild

This document defines the safe path for rebuilding the historical local
quarantine backup without mutating canonical shipped data.

## Source snapshot

- Repository: `https://github.com/ganjoor/ganjoor-data`
- Pinned source commit: `a64968e78425b2e8c7904fbdf5289fba8251a757`
- Source generation timestamp: `2026-09-12T12:47:59.2264145Z`
- Source snapshot: 240 poets / 135319 poems

The pinned commit is intentional. Do not rebuild from a moving `main` URL when a
reproducible release candidate is being prepared.

## Provenance of the quarantined rows

The current canonical database does **not** contain a `poems_quarantine` table.
The historical recovery input is the local ignored file:

```text
data/quarantined_poems_backup.json
```

Git commit `c21ea7646215485c53768976943b4fc1934f3cbf` records the historical
operation as quarantining **215 corrupted poem rows** while keeping **2274
verified-clean poems** in the 31 MB canonical database. The backup file itself
is deliberately ignored and is not part of the public repository.

Because the backup is local-only, a clean checkout cannot reproduce its contents
without obtaining the local file from the maintainer. The rebuild tool therefore
supports both the historical JSON backup and, for compatibility with older local
states, a SQLite quarantine table.

## Important rights distinction

The Ganjoor repository describes itself as a public, git-tracked export of Ganjoor
poetry content and excludes user-account-linked data. The repository does
**not** contain a `LICENSE` file. Therefore this project must not manufacture a
license for the compilation, metadata, summaries, or other editorial material.

### 1. Underlying poem texts

For classical authors such as Hafez, Saadi, Ferdowsi, Bidel, and similar historical
poets, the underlying original literary works are expected to be outside the
normal copyright term because of their age. This is a **public-domain candidate
status**, not an automatic release approval. The project must still consider the
applicable jurisdiction and whether the shipped text includes any separately
protectable modern editorial layer, such as a translation, critical edition,
annotation, summary, correction, formatting, or other contributed material.

Accordingly, do not record `Public Domain` as a universal legal conclusion for an
entire Ganjoor record merely because the named poet is historical.

### 2. Ganjoor compilation and editorial structure

The dataset's collection, identifiers, category hierarchy, metadata, summaries,
formatting, and other editorial structure are distinct from the underlying
classical works. The upstream repository currently provides no explicit LICENSE
file for that compilation. Its public availability is evidence of provenance,
not by itself a grant of redistribution rights.

Therefore the SIMORGH rights ledger must keep the Ganjoor-derived compilation /
editorial layer **NOT_VERIFIED** until a human maintainer has reviewed a concrete
legal basis for redistributing the exact fields that SIMORGH intends to ship.

This distinction is deliberate:

```text
original classical work            -> likely public-domain candidate
Ganjoor compilation / structure    -> rights not established by LICENSE file
modern editorial/translation text  -> must be assessed separately
SIMORGH release decision           -> human decision required
```

## Rebuild rule

`scripts/prepare_ganjoor_rebuild.py` is deliberately non-destructive:

1. It accepts either `data/quarantined_poems_backup.json` or a local SQLite
   quarantine table.
2. It resolves poet/title pairs against the pinned Ganjoor snapshot.
3. It downloads the matched poem JSON and reconstructs text from ordered `Verses`.
4. It enforces the 3000-character row limit.
5. For generic titles such as `مجموعه اشعار`, an optional text-evidence fallback
   can fetch poems for the identified poet and return ranked candidates. It does
   **not** silently select a fuzzy match.
6. It writes a reviewable candidate JSON file.
7. It never replaces `data/simorgh_full.db` and never edits the local backup.

A human must review the candidate before any database mutation or commit.

## Local invocation

Primary invocation using the historical backup:

```bash
cd ~/simorgh
mkdir -p rebuild_staging
python3 scripts/prepare_ganjoor_rebuild.py \
  --input-json data/quarantined_poems_backup.json \
  --output rebuild_staging/ganjoor_candidate.json \
  --enable-text-fallback
```

Compatibility invocation for an older local SQLite quarantine state:

```bash
python3 scripts/prepare_ganjoor_rebuild.py \
  --db data/simorgh_full.db \
  --table poems_quarantine \
  --output rebuild_staging/ganjoor_candidate.json
```

The command returns exit code `0` only when every input row has a unique matching
upstream poet/title and every reconstructed row is at or below the 3000-character
limit. Otherwise the non-zero result is intentional evidence that manual review
is still required.

## Multi-poem / concatenated rows

Some historical quarantine rows have reasons such as
`concatenated-multi-poem (len > 3000)` and may contain several poems under a
single generic title. These rows must not be treated as one canonical poem.
The current text fallback returns ranked upstream candidates only; segmentation
and final replacement remain human-reviewed operations.

## Release gate

Do not change `compliance/ASSET_RIGHTS.csv` to `VERIFIED` merely because the
source is official or because the underlying poet is historical. The rights ledger
should be updated only after the exact redistribution basis, attribution
requirements, and included derivative/editorial fields have been reviewed and
accepted by the human maintainer.

Do not commit `rebuild_staging/` or any local quarantine backup containing private
or unverified source material.
