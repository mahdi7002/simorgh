# Verse database v2 rebuilt from Ganjoor (2026-10-23)

Builder version 2 (scripts/build_verse_db.py), 54 poets (the poets also present in the previous database), pinned
Ganjoor export. Build statistics:

    {
     "poets": 54,
     "poems": 60664,
     "verses": 1533438,
     "bad_files": 0,
     "seconds": 177.6,
     "bytes": 493535232,
    }

## Source-to-database audit

Every source row was compared with its database row by source path and VOrder (text, position, couplet index, bait
number, side, normalised index text), and every poem with its metadata:

    SOURCE_COMMIT=a64968e78425b2e8c7904fbdf5289fba8251a757
    SOURCE_POEM_FILES=61566
    SOURCE_RECORDS=1553660
    SOURCE_INDEXABLE_ROWS=1533438
    DATABASE_POEMS=60664
    DATABASE_VERSE_ROWS=1533438
    DATABASE_FTS_VERSE_COUNT=1533438
    INTEGRITY_CHECK=ok
    FOREIGN_KEY_ERRORS=0
    FTS_PROBE_OK=True
    COMMENT	165
    PARAGRAPH	20057
    EXACT_SOURCE_ROW	1533438
    POEM_METADATA_AND_ROWS_EXACT	60664
    SOURCE_HAS_NO_INDEXABLE_ROWS_OK	902
    ROW_AND_METADATA_ISSUE_COUNT=0
    AUDIT_RESULT=PASS

What this does and does not show: the audit recomputes the builder's own extraction rules, so it shows that nothing
was lost or altered relative to those rules. It does not show that the rules are right for every downstream use.

## What the first audit found and version 2 fixed

An earlier line-level audit of version 1 found prose paragraphs indexed as verses, the second side of CenteredVerse2
rows recorded wrongly, and the source position type not kept. Version 2 excludes Paragraph and Comment rows, fails
closed on unknown positions, and stores source_path, source_full_title, source_vorder, source_position and
source_couplet_index. 902 source files contain only prose or comments and therefore have no poem record.

## Evaluation on this database

eval/run_eval.py --no-llm --attr-n 300, seeds 11, 23, 37 (offline sections). Rows as printed:

    seed 11: | E. Verse attribution | EASY: query = first 6 words of a random indexed verse, seed=11, n=300; lookup=app.knowledge.poetry_lookup | answered 298/300, answered-accuracy 298/298, abstained-with-poet-in-candidates 2/2, chimera false-accepts 1/140 |
    seed 11: | E+. Verse attribution, middle 4 words (no prefix) | same sample, same lookup | answered 290/300, answered-accuracy 290/290, abstained-with-poet-in-candidates 10/10 |
    seed 11: | E+. Verse attribution, prefix, last letter of a word dropped | same sample, same lookup | answered 97/300, answered-accuracy 94/97, abstained-with-poet-in-candidates 187/203 |
    seed 11: | E+. Verse attribution, prefix, a middle letter dropped | same sample, same lookup | answered 96/300, answered-accuracy 94/96, abstained-with-poet-in-candidates 186/204 |
    seed 11: | E+. Verse attribution, prefix, two adjacent letters swapped | same sample, same lookup | answered 97/300, answered-accuracy 95/97, abstained-with-poet-in-candidates 188/203 |
    seed 23: | E. Verse attribution | EASY: query = first 6 words of a random indexed verse, seed=23, n=300; lookup=app.knowledge.poetry_lookup | answered 299/300, answered-accuracy 299/299, abstained-with-poet-in-candidates 1/1, chimera false-accepts 0/147 |
    seed 23: | E+. Verse attribution, middle 4 words (no prefix) | same sample, same lookup | answered 288/300, answered-accuracy 288/288, abstained-with-poet-in-candidates 12/12 |
    seed 23: | E+. Verse attribution, prefix, last letter of a word dropped | same sample, same lookup | answered 101/300, answered-accuracy 100/101, abstained-with-poet-in-candidates 186/199 |
    seed 23: | E+. Verse attribution, prefix, a middle letter dropped | same sample, same lookup | answered 95/300, answered-accuracy 95/95, abstained-with-poet-in-candidates 192/205 |
    seed 23: | E+. Verse attribution, prefix, two adjacent letters swapped | same sample, same lookup | answered 96/300, answered-accuracy 96/96, abstained-with-poet-in-candidates 191/204 |
    seed 37: | E. Verse attribution | EASY: query = first 6 words of a random indexed verse, seed=37, n=300; lookup=app.knowledge.poetry_lookup | answered 298/300, answered-accuracy 298/298, abstained-with-poet-in-candidates 2/2, chimera false-accepts 0/144 |
    seed 37: | E+. Verse attribution, middle 4 words (no prefix) | same sample, same lookup | answered 283/300, answered-accuracy 283/283, abstained-with-poet-in-candidates 17/17 |
    seed 37: | E+. Verse attribution, prefix, last letter of a word dropped | same sample, same lookup | answered 111/300, answered-accuracy 111/111, abstained-with-poet-in-candidates 176/189 |
    seed 37: | E+. Verse attribution, prefix, a middle letter dropped | same sample, same lookup | answered 109/300, answered-accuracy 109/109, abstained-with-poet-in-candidates 181/191 |
    seed 37: | E+. Verse attribution, prefix, two adjacent letters swapped | same sample, same lookup | answered 110/300, answered-accuracy 110/110, abstained-with-poet-in-candidates 183/190 |

This database is not the one behind docs/evidence/ATTRIBUTION_HELDOUT.md: poets, edition wording and row structure
differ, so the numbers are not directly comparable with that table.
