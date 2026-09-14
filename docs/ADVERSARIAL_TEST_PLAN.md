# SIMORGH Adversarial Security Test Plan

This plan treats the model as an untrusted component and assumes users, prompts, retrieved documents, plugins, and external providers may be adversarial.

## Test families

| Family | Attack goal | Required evidence |
|---|---|---|
| Prompt injection | Override system intent, tool policy, or evidence rules | Regression corpus with expected refusal/containment |
| Sensitive disclosure | Exfiltrate memory, paths, secrets, prompts, or headers | Automated tests showing redaction/isolation |
| Supply chain | Introduce unsafe dependency/model/plugin behavior | SBOM + dependency scan + rights ledger |
| Data/model poisoning | Insert false or malicious knowledge | Provenance and source-status tests |
| Output handling | Turn generated text into unsafe commands, paths, HTML, or headers | Input/output boundary tests |
| Excessive agency | Cause autonomous mutation, privilege gain, network escalation, or tool expansion | Human-gate tests and denied-action cases |
| Prompt leakage | Extract system prompts or private policy | Leakage regression cases |
| Retrieval weakness | Poison or cross-tenant retrieved context | Source isolation and provenance tests |
| Misinformation | Cause unsupported factual/citation claims | Evidence-sensitive reviewer tests |
| Resource exhaustion | Oversized bodies, queries, pagination, repeated calls | Size/time/rate-limit controls |

## Release rule

A newly introduced model provider, tool, memory surface, upload path, or privileged capability is not IMPLEMENTED until it has at least one abuse-oriented regression test and a CI path that executes it.

## Deployment rule

Internet-facing deployment requires TLS at the deployment edge, explicit allowed origins, authentication, rate limiting, monitoring, incident response, and a reviewed privacy/data-processing configuration. The repository can enforce some of these controls but cannot replace the deployment environment.

## Evidence boundary

A passing adversarial test demonstrates only the tested case. It does not prove that SIMORGH is impossible to jailbreak, misuse, or break.

## Reference

The 2025 OWASP Top 10 for LLM/GenAI applications identifies prompt injection, sensitive information disclosure, supply chain vulnerabilities, data/model poisoning, improper output handling, excessive agency, system prompt leakage, vector/embedding weaknesses, misinformation, and unbounded consumption as key risks. See the project references in `docs/LEGAL_AND_COMPLIANCE.md`.
