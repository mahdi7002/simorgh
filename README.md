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
- **Provider-neutral agent governance:** agent-like workflows use native SIMORGH governance contracts rather than a mandatory vendor SDK.

## The core principles

### Proposal ≠ Command

A system may propose an action or change. It does not gain authority merely by proposing it.

### Known ≠ Inferred

Retrieved or verified information must not be silently presented as though it were directly known when it is actually an inference.

### Provenance > elegance

When evidence matters, SIMORGH prefers traceability and an honest limitation over a polished unsupported answer.

### Human authority remains explicit

Self-improvement and knowledge mutation are governed surfaces. Automatic mutation is disabled unless a policy and human gate explicitly permit the operation.

### Provider ≠ Authority

A local model, cloud agent, MCP server, coding assistant, or other external executor may provide capability, but none becomes the governing authority of SIMORGH.

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
| Provider-neutral governance contracts | IMPLEMENTED | `core/orchestration/contracts.py` + regression tests |
| Hosted external-bind authentication boundary | IMPLEMENTED | adversarial regression tests |
| Hosted session isolation | IMPLEMENTED | runtime hardening tests |
| AI interaction disclosure metadata | IMPLEMENTED | runtime hardening tests |
| Bounded voice input | IMPLEMENTED | runtime hardening tests |
| Database-first no-model fallback | IMPLEMENTED | user runtime regression tests |
| Hardware-aware local model catalog | IMPLEMENTED | user runtime regression tests |
| SHA-256 model verification | IMPLEMENTED | user runtime regression tests |
| Local llama.cpp backend lifecycle | IMPLEMENTED | runtime path + user runtime tests |
| Self-contained x86_64 AppImage packaging | IMPLEMENTED | AppImage build workflow + packaging tests |
| Automatic knowledge mutation | DISABLED | Human gate required |
| Governed external tool adapters | EXPERIMENTAL | See Issue #7 |
| Full external tool-calling | EXPERIMENTAL | Persona-specific tools remain isolated |
| Semantic/LLM dispatcher | PLANNED | Lightweight rules used by default |
| Multi-agent execution fabric | PLANNED | Native contracts documented in `docs/AGENT_FABRIC.md` |
| Native packages for other platforms/architectures | PLANNED | AppImage is currently x86_64 Linux |

## User-first installation

برای کاربر عادی، مسیر اصلی روی Linux این است:

```bash
./install.sh
```

برای کاربری که فقط یک فایل اجرایی می‌خواهد، بستهٔ self-contained آمادهٔ AppImage نیز در دسترس است:

```bash
chmod +x SIMORGH-x86_64.AppImage
./SIMORGH-x86_64.AppImage
```

AppImage شامل Python، dependencyهای اصلی runtime، رابط وب و پایگاه دانش canonical است. داده‌های شخصی، حافظه، تنظیمات و مدل‌های دانلودشده بیرون از AppImage نگه داشته می‌شوند.

launcher در سطح کاربر اجرا می‌شود، مسیر داده را در اولین اجرا تعیین می‌کند، runtime را روی loopback بالا می‌آورد و رابط سیمرغ را در مرورگر باز می‌کند. وقتی systemd کاربر در دسترس باشد، همان نصب یک سرویس پایدار با `Restart=always` و auto-start ایجاد می‌کند؛ در صورت پشتیبانی systemd، linger نیز فعال می‌شود تا هسته پس از خروج از نشست متوقف نشود.

مدل زبانی اجباری نیست. بدون مدل، پایگاه دانش محلی همچنان قابل استفاده است. دانلود مدل تنها پس از اقدام کاربر انجام می‌شود و پیش از ثبت، SHA-256 و اطلاعات provenance کنترل می‌شوند.

وضعیت سرویس:

```bash
systemctl --user status simorgh.service
journalctl --user -u simorgh.service -n 80 --no-pager
```

راهنمای کامل کاربر: [`docs/USER_INSTALL.md`](docs/USER_INSTALL.md)
راهنمای AppImage: [`docs/APPIMAGE.md`](docs/APPIMAGE.md)
گزارش ممیزی عملیاتی نهایی و شواهد اجرایی: [`docs/FINAL_OPERATIONAL_AUDIT_2026-09-18.md`](docs/FINAL_OPERATIONAL_AUDIT_2026-09-18.md)
ممیزی تکرارپذیر: `./scripts/simorgh-final-audit.sh`

## Developer quick start

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

Without a local model server, SIMORGH falls back to deterministic local knowledge retrieval where a matching source exists. It must never pretend that a model response exists when no model is available.

With a local `llama-server`, the local provider can be used for persona responses. The user runtime can install and start a verified CPU llama.cpp backend on supported hosts.

## Hosted trust boundary

The default service bind is loopback-only. A non-loopback bind without an explicit `SIMORGH_KEY` fails closed. For external binding, protected endpoints require `x-token`, while `/health` remains available for health checks.

External sessions must provide an opaque `X-SIMORGH-SESSION` value. SIMORGH hashes this identifier before storing it with memory so different hosted sessions do not collapse into the same default conversation bucket.

Generation endpoints return explicit AI-disclosure metadata and a machine-readable `X-SIMORGH-AI-GENERATED: true/false` response header that matches whether a local language model generated the text. A deployment UI must render a clear human-visible AI disclosure where required.

For internet-facing operation, TLS, rate limiting, allowed-host/origin policy, incident response, operational logging controls, and provider contracts remain deployment responsibilities.

## Minimal demo

```bash
python3 demo/simorgh_minimal.py --test
python3 demo/simorgh_minimal.py "عدالت چیست؟"
```

For the detailed first-run path, see [`QUICKSTART.md`](QUICKSTART.md), [`docs/USER_INSTALL.md`](docs/USER_INSTALL.md), and [`docs/APPIMAGE.md`](docs/APPIMAGE.md).

## Agent fabric

SIMORGH intentionally borrows architectural lessons from modern agent systems without depending on them. See [`docs/AGENT_FABRIC.md`](docs/AGENT_FABRIC.md) for the provider-neutral lifecycle, capability boundary, evidence artifacts, and Human Gate model.

## Repository map


### Project continuity

For new AI collaborators and developers, start with the Git-readable project map:

- [`docs/PROJECT_MAP.md`](docs/PROJECT_MAP.md) — architecture, verification rules, onboarding, workspace boundaries, and current authorized scope
- [`docs/AI_WORK_CONTRACT.md`](docs/AI_WORK_CONTRACT.md) — evidence, change-control, and unplanned-work rules

These documents are deliberately separate from volatile runtime state. Always inspect the
actual checkout and run the declared tests before making claims about the live system.
