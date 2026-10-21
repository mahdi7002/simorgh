# Real-world cases seen on 2026-10-20 (limitations, not fixed before submission)

These came from a fresh local run, not from the evaluation set. They are recorded because the evaluation
questions were derived from the database, so they cannot reveal this kind of failure. Per docs/ROADMAP_2026-10.md,
typo- and variant-robust matching is frozen until after submission and is reported as a limitation.

## Case 1: popular wording, edition wording and quotation by another poet
The database stores the opening line of the Masnavi under the poet's own name with this wording: «بشنو این نی چون شکایت می‌کند». The popular wording of the same line is found only inside a verse by another poet (marked as a quotation with «). A user typing the popular wording gets the other poet.
Verse attribution currently treats a single exact hit as certain. A hit that is a quotation inside another poet's
work, or an edition variant, is not recognised as such.

## Case 2: a work that does not exist
Asked about a book with a plausible-sounding title attributed to a real poet, the local model wrote a confident
description. Fixed in the answer layer (not in retrieval): a quoted title after a work word (book, divan, collected
works, novel, work) that cannot be verified in the local catalogue now gets a fixed warning under the answer.

## Case 3: model slot configuration
With the secondary model server stopped, the core reported "model unavailable" even though the primary server was
healthy, because the quality slot pointed at a port nothing listened on. Fixed by pointing both slots at the same server.

## Suggested use
Collect 30 to 50 verse and work questions typed by other people and report them as a separate, non-database-derived set.
