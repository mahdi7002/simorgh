# سیمرغ · SIMORGH

**An open-source, offline-first experiment in human-accountable AI.**

**هوش در خدمت انسان، نه انسان در خدمت هوش**

SIMORGH explores a practical question:

> **How capable can an AI system become while the human remains the owner and final authority?**

This repository is not a claim to AGI, superintelligence, or industrial-scale model performance. It is a working software experiment built around constraints that are easy to say and harder to enforce in code: local-first operation, user-owned memory, provenance, bounded tools, verification, and human gates for consequential self-improvement.

---

## Why SIMORGH?

Most AI projects are introduced through model size, benchmark scores, or a cloud service. SIMORGH starts somewhere else: **authority**.

Its design vocabulary is deliberately simple:

- **Proposal ≠ Command** — the system may propose; it does not automatically receive authority to act.
- **Known ≠ Inferred** — retrieved evidence, model inference, and user-provided facts should not be silently mixed.
- **Provenance > elegance** — an answer that exposes where its evidence came from is preferable to a smoother unsupported answer.
- **Human Gate** — consequential changes and increases in authority require human approval.
- **Offline-first** — the core should remain useful without a mandatory cloud account, API key, or network connection.
- **Graceful degradation** — missing optional dependencies or a missing local model should produce an honest limitation, not a fake success.

The project is developed with human direction and AI-assisted code generation/review. The repository itself is treated as evidence: **verification over claims**.

---

## What you can run today

The public repository currently contains a runnable Python service, a dependency-free minimal demo, 12 personas, shared request orchestration, provenance-aware memory, a deterministic reviewer gate, sentence-level citation verification, and governed self-improvement policy paths.

The minimal demo can run immediately with Python alone:

```bash
python3 demo/simorgh_minimal.py --test
python3 demo/simorgh_minimal.py "عدالت چیست؟"
```

With a local OpenAI-compatible LLM endpoint, the demo can use local generation. Without one, it falls back to its small embedded offline demonstration corpus and explicitly labels the mode.

For the full service:

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

Then:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/personas
curl -s -X POST http://127.0.0.1:8000/chat -d "query=سلام&agent=hakim"
```

If no local model is available, the service must report that limitation rather than pretending that a model generated the answer.

See [`QUICKSTART.md`](QUICKSTART.md) for the shortest installation path.

---

## The architecture in one line

**Question → evidence / memory → shared request state → persona → reviewer → verified response → human decision**

Not every path in that sentence is equally mature yet. The capability matrix below is the source of truth for current implementation status.

---

## Capability matrix

| Capability | Status | Verification / boundary |
|---|---|---|
| Offline-first core | **IMPLEMENTED** | CI runtime audit |
| Local LLM provider | **IMPLEMENTED** | Runtime-dependent |
| 12 personas | **IMPLEMENTED** | `/personas` + tests |
| Shared request blackboard | **IMPLEMENTED** | `core/orchestration/` |
| Lightweight dispatcher | **IMPLEMENTED** | `core/orchestration/dispatcher.py` |
| Deterministic reviewer gate | **IMPLEMENTED** | reviewer regression tests |
| Sentence-level citation verification | **IMPLEMENTED** | reviewer verification tests |
| Provenance memory | **IMPLEMENTED** | SQLite regression tests |
| Governed self-improvement | **IMPLEMENTED** | policy regression tests |
| Automatic knowledge mutation | **DISABLED** | Human gate required |
| Full external tool-calling | **EXPERIMENTAL** | Persona-specific tools remain isolated |
| Semantic / LLM dispatcher | **PLANNED** | Lightweight rules are used by default |
| Public release package | **PLANNED** | No GitHub release yet |

### Verification policy

A capability is considered **implemented** only when the repository contains:

1. an executable implementation,
2. a regression test,
3. a CI path that executes that test.

Anything else is documented as experimental, planned, or disabled.

---

## Governance and self-improvement

SIMORGH treats self-improvement as a governance problem, not merely an optimization problem.

The current policy distinguishes between changes that are informational/reversible and changes that can alter execution, authority, networking, evaluators, or governing rules. Higher-risk changes are gated by human approval.

The intended principle is:

**The system can help design its next version. It does not own the right to approve that version.**

This is an engineering boundary, not a claim that the system is magically safe.

---

## Persian identity and knowledge

The project includes Persian cultural and literary material and 12 wisdom-oriented personas. These are not presented as replacements for factual verification or human judgment.

Cultural identity is part of the interface and knowledge layer. It is not a license to invent quotations, attribute text without evidence, or turn literary interpretation into factual certainty.

---

## What SIMORGH is not

SIMORGH is **not** claiming to be:

- AGI or artificial superintelligence
- a replacement for human judgment
- a guarantee against AI failure or misuse
- a competitor to frontier-scale industrial models
- a fully autonomous agent with unrestricted computer access
- a finished product

The interesting question is narrower and more testable: **can authority boundaries, provenance, verification, and human ownership be made concrete in an AI system rather than left as product slogans?**

---

## Current limitations

The public repository is still an evolving engineering project. Local model quality depends on the model and hardware available to the user. Some richer data, speech, PDF, and tool workflows are optional or experimental. A planned capability is not a hidden promise.

If something is unavailable, the preferred behavior is to say so.

---

## Contributing

Start with an Issue for a substantial change, then keep pull requests small, inspectable, and testable. Governance-sensitive changes should preserve the human-approval boundaries already established in the repository.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).

---

## License and author

- **License:** MIT
- **Author:** Mahdi Jafari Najafabadi
- **Primary repository:** [`mahdi7002/simorgh`](https://github.com/mahdi7002/simorgh)

> **Run it. Inspect it. Break it. If the claim does not survive the test, change the claim or change the code.**
