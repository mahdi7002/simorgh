# SIMORGH Quran Translation Source

## Exact upstream source

SIMORGH's Persian Quran translation asset is identified as the Tanzil translation `fa.ansarian`:

- Official source: https://tanzil.net/trans/fa.ansarian
- Name: انصاریان
- Translator: Hussain Ansarian / حسین انصاریان
- Language: Persian
- Tanzil translation ID: `fa.ansarian`
- Last update stated by Tanzil: July 6, 2011
- Expected translation rows: 6236

Tanzil documents its translation file format as UTF-8, with one line per aya and exactly 6236 translation lines. Source documentation: https://tanzil.net/docs/adding_new_translations

## Reproducible build

Run:

```bash
python scripts/build_tanzil_quran_db.py
```

The script downloads the translation directly from the official Tanzil URL, validates the 6236-row structure, stores the translation rows in `data/grid/quran.db`, and writes a reproducibility manifest to `docs/TANZIL_FA_ANSARIAN_MANIFEST.json`.

The script does not rewrite, normalize, summarize, correct, or translate the Tanzil rows. The SQLite display prefix (`سوره N آیه M |`) is SIMORGH indexing metadata around the verbatim translation string.

To verify the shipped database against the live upstream source:

```bash
python scripts/verify_tanzil_quran_db.py
```

## Rights boundary

Tanzil's translation page states that translations provided there are for non-commercial purposes only. It also states that use otherwise requires permission from the translator or publisher. The same page identifies `fa.ansarian` as the Hussain Ansarian Persian translation: https://tanzil.net/trans/

This is separate from Tanzil's Quran-text license. The Creative Commons Attribution 3.0 text license applies to Tanzil Quran text, not automatically to the Ansarian translation: https://tanzil.net/docs/Text_License

SIMORGH can therefore establish provenance to Tanzil for `fa.ansarian` through the reproducible source URL, but the asset must remain `NOT_VERIFIED` for redistribution/commercial release until the applicable translation permission conditions are satisfied.

## Release policy

A successful source verification, hash calculation, SQLite integrity check, or CI pass does not itself create permission to redistribute the translation. The compliance ledger must remain conservative until the human maintainer records the required permission or a rights basis that explicitly covers the intended distribution mode.
