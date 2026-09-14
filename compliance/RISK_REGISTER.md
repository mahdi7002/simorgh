# SIMORGH Adversarial Risk Register

Severity uses: P0 = release blocker, P1 = high priority, P2 = hardening/operational.

| ID | Risk | Current control | Residual gap | Severity | Evidence |
|---|---|---|---|---|---|
| AI-01 | Prompt injection changes model behavior or tool selection | Deterministic tool planner, bounded registry, separate evidence context | Dedicated malicious prompt regression corpus still needed | P1 | OWASP LLM01 |
| AI-02 | Sensitive information disclosure | Local-first default, session hashing, no response-header echo | Hosted privacy/retention controls and provider contracts incomplete | P0 | OWASP LLM02 |
| AI-03 | Supply-chain compromise | CI hygiene, declared dependencies, planned SBOM | Exact release SBOM and dependency vulnerability scan not yet a release blocker | P0 | OWASP LLM03, NIST SSDF |
| AI-04 | Data/model poisoning | Provenance fields and local controlled datasets | Source/rightsholder verification ledger incomplete | P0 | OWASP LLM04 |
| AI-05 | Improper output handling | FastAPI validation, bounded dashboard inputs, explicit AI disclosure | Broader output/content security test suite needed | P1 | OWASP LLM05 |
| AI-06 | Excessive agency | No arbitrary shell tool, human-gated self-improvement, bounded tools | More adversarial end-to-end tool abuse tests needed | P0 | OWASP LLM06 |
| AI-07 | System-prompt leakage | Prompt in internal context only | Dedicated leakage regression corpus needed | P1 | OWASP LLM07 |
| AI-08 | Vector/embedding weaknesses | Current core does not grant autonomous vector tool authority | Future semantic retrieval needs poisoning/access controls | P1 | OWASP LLM08 |
| AI-09 | Misinformation | Evidence gate, provenance, no fabricated fallback in minimal demo | Truthfulness benchmark and domain-specific evals needed | P0 | OWASP LLM09 |
| AI-10 | Unbounded consumption / resource exhaustion | Timeouts, pagination limits, voice body size limit | Global rate limiting requires deployment edge or distributed limiter | P1 | OWASP LLM10 |
| WEB-01 | External API exposure without authentication | Fail-closed non-loopback bind + token middleware | Hosted TLS/rate-limit/proxy policy still deployment-specific | P0 | OWASP A07/A02 |
| WEB-02 | Request/resource abuse | Bounded query/page/body inputs | Full rate-limit and concurrency controls not in app | P1 | OWASP A06/A10 |
| DATA-01 | Shared hosted memory between users | Session header required externally; hashed session storage | Identity provider or per-user auth remains deployment-specific | P0 | Privacy design |
| DATA-02 | Data-rights failure | Data map and explicit release blockers | Actual privacy notice, retention and deletion API/package needed for hosted product | P0 | GDPR/UK GDPR/PDPA/PIPL/etc. |
| LEGAL-01 | Embedded asset rights not established | Rights ledger schema | Rights verification incomplete | P0 | Copyright/license review |
| CLAIM-01 | Unsupported safety/privacy/autonomy claims | README non-claims and release gate | Marketing review required on every release | P1 | FTC / AI Act transparency |

## Adversarial testing rule

Any new tool, provider, memory surface, upload surface, or autonomous mutation capability must add a regression test before being marked IMPLEMENTED. Tests must include at least one abuse-oriented case, not only the happy path.
