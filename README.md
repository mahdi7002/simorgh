# سیمرغ · SIMORGH

**An open-source, offline-first experiment in human-accountable AI.**

**هوش در خدمت انسان، نه انسان در خدمت هوش**

SIMORGH explores a practical question:

> **How capable can an AI system become while the human remains the owner and final authority?**

SIMORGH is not presented as AGI, a replacement for frontier labs, or a system that is incapable of failure. It is a bounded engineering experiment focused on human authority, inspectability, provenance, local execution, and honest capability reporting.

## What SIMORGH is

- **Offline-first:** the core can run without a mandatory cloud account, API key, or internet connection.
- **Human-accountable:** proposals are not commands, and knowledge mutation is gated rather than silently applied.
- **Evidence-aware:** retrieved evidence and model-generated text are kept conceptually distinct, with provenance and reviewer checks.
- **User-owned memory:** memory is treated as user data, with explicit controls rather than invisible personalization.
- **Bounded tools:** tool access is intended to be explicit, local-first, deterministic where practical, and constrained by policy.
- **Provider-agnostic:** a local model is the preferred path; external providers are optional rather than required.

## The core principles

### Proposal ≠ Command

A system may propose an action or change. It does not gain authority merely by proposing it.

### Known ≠ Inferred

Retrieved or verified information must not be silently presented as though it were directly known when it is actually an inference.

### Provenance > elegance

When evidence matters, SIMORGH prefers traceability and an honest limitation over a polished unsupported answer.

### Human authority remains explicit

Self-improvement and knowledge mutation are governed surfaces. Automatic mutation is disabled unless a policy and human gate explicitly permit the operation.

## Verification policy

SIMORGH uses a deliberately conservative capability matrix. A capability is considered **IMPLEMENTED** only when the repository contains:

1. an executable implementation,
2. a regression test,
3. a CI path that executes the test.

Otherwise it is documented as **EXPERIMENTAL**, **PLANNED**, or **DISABLED**.

## Current capability matrix

| Capability | Status | Verification |
|---|---|---|
| Offline-first core | IMPLEMENTED | CI runtime audit |
| Local LLM provider | IMPLEMENTED | Runtime-dependent |
| 12 personas | IMPLEMENTED | `/personas` + tests |
| Shared request blackboard | IMPLEMENTED | `core/orchestration/` |
| Lightweight dispatcher | IMPLEMENTED | dispatcher tests |
| Deterministic reviewer gate | IMPLEMENTED | reviewer tests |
| Sentence-level citation verification | IMPLEMENTED | reviewer regression tests |
| Provenance memory | IMPLEMENTED | SQLite regression tests |
| Governed self-improvement | IMPLEMENTED | policy regression tests |
| Automatic knowledge mutation | DISABLED | Human gate required |
| Governed external tool adapters | EXPERIMENTAL | See Issue #7 |
| Full external tool-calling | EXPERIMENTAL | Persona-specific tools remain isolated |
| Semantic/LLM dispatcher | PLANNED | Lightweight rules used by default |
| Public release package | PLANNED | Release gate not yet satisfied |

## Quick start

```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt

python -c "import main; print('OK', len(main.app.routes))"
python main.py
```

Then, in another terminal:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/personas
curl -s -X POST http://127.0.0.1:8000/chat -d "query=سلام&agent=hakim"
```

Without a local model server, SIMORGH should report that the model is unavailable rather than pretending that a model response exists.

With a local `llama-server`, the local provider can be used for persona responses. Exact model configuration is intentionally runtime-dependent.

Minimal demo:

```bash
python3 demo/simorgh_minimal.py --test
python3 demo/simorgh_minimal.py "عدالت چیست؟"
```

For the detailed first-run path, see [`QUICKSTART.md`](QUICKSTART.md).

## Repository map

| Path | Purpose |
|---|---|
| `main.py` / `cli.py` | Service and command-line entry points |
| `core/` | Chat, identity, memory, retrieval, orchestration, portable paths |
| `agents/` | Persona and agent definitions |
| `dashboard/` | Web interface |
| `demo/` | Minimal runnable demonstrations |
| `tests/` | Regression and governance tests |
| `.github/workflows/` | CI and runtime/hygiene verification |
| `docs/` | Architecture, verification, launch and development notes |

Optional integrations such as speech, PDF/OCR and richer metrics are intentionally separated from the minimal core installation.

## What SIMORGH does not claim

SIMORGH does **not** claim to be:

- AGI or artificial general intelligence.
- A replacement for frontier AI systems.
- Impossible to jailbreak, misuse, or break.
- Fully autonomous or independently authoritative.
- A scientifically proven solution to AI alignment.
- A system with capabilities that have not been demonstrated and tested.

Those boundaries are part of the project, not an embarrassment to hide.

## Development philosophy

The project is developed under human direction with AI-assisted code generation and review. The human author determines requirements, architecture and acceptance. AI-generated code is treated as code to inspect and test, not as authority.

The project favors:

- small, inspectable changes,
- executable demonstrations,
- regression tests,
- cold-start testing,
- explicit failure states,
- no secret telemetry,
- no mandatory API keys,
- no arbitrary shell execution as a tool capability,
- and no silent elevation of model output into verified knowledge.

## Public launch status

The repository is being consolidated before the first public announcement. No public release is claimed until the release gate is satisfied.

See [`docs/PUBLIC_LAUNCH.md`](docs/PUBLIC_LAUNCH.md) for the current public positioning and release checklist.

## License

MIT. See [`LICENSE`](LICENSE).

## Author

Mahdi Jafari Najafabadi · Yazd, Iran

For bugs, evidence gaps, or proposed changes, open an Issue first and keep pull requests small and testable.
