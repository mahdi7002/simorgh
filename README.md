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
| Hosted external-bind authentication boundary | IMPLEMENTED | adversarial regression tests |
| Hosted session isolation | IMPLEMENTED | runtime hardening tests |
| AI interaction disclosure metadata | IMPLEMENTED | runtime hardening tests |
| Bounded voice input | IMPLEMENTED | runtime hardening tests |
| Automatic knowledge mutation | DISABLED | Human gate required |
| Governed external tool adapters | EXPERIMENTAL | See Issue #7 |
| Full external tool-calling | EXPERIMENTAL | Persona-specific tools remain isolated |
| Semantic/LLM dispatcher | PLANNED | Lightweight rules used by default |
| Public release package | PLANNED | Release gate not yet satisfied |

## Local quick start

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

## Hosted trust boundary

The default service bind is loopback-only. A non-loopback bind without an explicit `SIMORGH_KEY` fails closed. For external binding, protected endpoints require `x-token`, while `/health` remains available for health checks.

External sessions must provide an opaque `X-SIMORGH-SESSION` value. SIMORGH hashes this identifier before storing it with memory so different hosted sessions do not collapse into the same default conversation bucket.

Generation endpoints return explicit AI-disclosure metadata and a machine-readable `X-SIMORGH-AI-GENERATED: true` response header. A deployment UI must render a clear human-visible AI disclosure where required.

For internet-facing operation, TLS, rate limiting, allowed-host/origin policy, incident response, operational logging controls, and provider contracts remain deployment responsibilities.

## Minimal demo

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
| `tests/` | Regression, governance, and adversarial tests |
| `compliance/` | Rights, privacy, jurisdiction, SBOM, and release controls |
| `.github/workflows/` | CI, runtime, hygiene, and compliance verification |
| `docs/` | Architecture, verification, launch, security, and legal/compliance notes |

Optional integrations such as speech, PDF/OCR and richer metrics are intentionally separated from the minimal core installation.

## Global compliance posture

SIMORGH is **not** represented as globally legally compliant. The repository includes a machine-checkable compliance audit and a strict human release gate.

See:

- [`docs/LEGAL_AND_COMPLIANCE.md`](docs/LEGAL_AND_COMPLIANCE.md)
- [`docs/ADVERSARIAL_TEST_PLAN.md`](docs/ADVERSARIAL_TEST_PLAN.md)
- [`compliance/GLOBAL_JURISDICTION_MATRIX.md`](compliance/GLOBAL_JURISDICTION_MATRIX.md)
- [`compliance/PRIVACY_DATA_MAP.md`](compliance/PRIVACY_DATA_MAP.md)
- [`compliance/ASSET_RIGHTS.csv`](compliance/ASSET_RIGHTS.csv)
- [`compliance/THIRD_PARTY_LICENSES.csv`](compliance/THIRD_PARTY_LICENSES.csv)
- [`compliance/RELEASE_SIGNOFF.md`](compliance/RELEASE_SIGNOFF.md)

The CI can generate an SPDX SBOM for the exact installed Python environment. The current release gate intentionally remains blocked until embedded asset rights and third-party license records are independently verified.

## What SIMORGH does not claim

SIMORGH does **not** claim to be:

- AGI or artificial general intelligence.
- A replacement for frontier AI systems.
- Impossible to jailbreak, misuse, or break.
- Fully autonomous or independently authoritative.
- A scientifically proven solution to AI alignment.
- A globally legally compliant product without deployment-specific review.
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
