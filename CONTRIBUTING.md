# Contributing to Simorgh

Simorgh is an offline-first Persian AI assistant built via AI-directed
development (design and verification by a human, implementation by AI
under direction). Contributions are welcome, with a few guiding principles:

## Core principles
- **No overengineering.** Prefer a single working tool over a multi-subsystem
  pipeline. See `docs/AGENTIC_ARCHITECTURE.md` for the reasoning.
- **CPU-first.** All core functionality must run on modest hardware
  (tested baseline: i5-4460, 8GB RAM, no GPU). Don't assume a GPU is present.
- **Provenance matters.** Any change touching Quranic or classical Persian
  text must preserve source attribution — no unsourced generated content
  presented as scripture or classical text.

## Before submitting a PR
1. Open an issue first for anything beyond a small fix, so the approach
   can be discussed.
2. Keep PRs scoped to one change.
3. Never commit: API keys, `.env` files, personal file paths, database
   snapshots, or files over 5MB (CI will reject these automatically).
4. Run the demo (`demo/simorgh_minimal.py`) if your change touches core
   chat/persona logic — it should still work standalone.

## Reporting issues
Use the bug report / feature request templates. Include logs where relevant.

## License
By contributing, you agree your contributions are licensed under the
project's MIT license.
