# Simorgh — سیمرغ

An offline-first Persian AI assistant platform. Built through AI-directed
development: every line of code in this repository was written by an AI
model (primarily Claude) under direction from the project's author —
[Mahdi Jafari Najafabadi](https://github.com/mahdi7002), who defines
requirements, reviews architecture, and verifies results, but does not
write code by hand.

## Quick start — zero setup required

The fastest way to see how the persona system works, with no
dependencies and no local model required:

```bash
python3 demo/simorgh_minimal.py --test
python3 demo/simorgh_minimal.py "عدالت چیست؟"
```

This minimal demo always produces a working response — if a local LLM
server is reachable it uses that, otherwise it falls back to an offline
public-domain wisdom set. It exists specifically so anyone cloning this
repo has something that runs immediately.

## What's in this repository

- `cli.py`, `main.py` — command-line and service entry points
- `core/engine/` — routing, memory, and understanding modules
- `agents/` — persona definitions (YAML system prompts)
- `dashboard/` — web dashboard front-end
- `demo/simorgh_minimal.py` — the always-working minimal example above
- `.github/workflows/repo-hygiene.yml` — automated guard that blocks
  oversized files, editor junk, and leaked secrets on every push

## Current status — being actively synced

This public repository is in the process of being brought in line with
the author's full local development version, which includes a larger
set of personas, a full-text search index across classical Persian
poetry and a verified Quranic text database, and local speech
recognition. That fuller version currently runs locally and is being
migrated here incrementally rather than dumped in all at once, so that
every commit stays reviewable and the repository stays clean (see the
hygiene guard above).

## Design principles

- **Offline-first.** The core system requires no API key and no
  internet connection to function.
- **Provider-agnostic.** Cloud AI providers are optional, disabled by
  default, and never hardcoded — the user chooses.
- **Verification over claims.** Nothing here is presented as tested or
  finished without being actually run and checked.

## Author

Built by [Mahdi Jafari Najafabadi](https://github.com/mahdi7002),
Yazd, Iran — an AI-directed product builder. More projects and context:
see the portfolio linked from this profile.

## License

No license file is included yet — this repository is not currently
licensed for reuse. A license will be added before any external
contribution is invited.
