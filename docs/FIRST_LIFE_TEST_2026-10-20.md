# First life test, 2026-10-20

Method: a fresh runtime directory (no prior memory), one session id, six interactions, then the process was stopped
and started again from the same directory. Model: the local 4B model through the shared server.

| Property | Result before this change |
|---|---|
| Conversations stored | yes (6 rows; still there after restart) |
| Conversations used to answer | no: the name given in turn 3 was not recalled in turn 4 or after restart |
| Honest about an unknown work | no: a detailed description of a non-existent book was generated |
| Verse attribution | one verse was attributed to a poet who quoted it (see REAL_WORLD_CASES_2026-10.md) |
| Nightly reflection | not running: the job fails at import and reads a table nothing writes |

What changed: the last four turns of the same session are now given to the model (off with SIMORGH_CHAT_MEMORY=off),
and unverifiable work titles get a fixed warning. Not changed on purpose: retrieval and attribution logic
(frozen until after submission), the nightly reflection job, the older /ask route.

Only the Mother supervisor keeps an incident, attempt, verification and lesson history; ordinary chat does not.
