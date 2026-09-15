# Security Policy

## Reporting a vulnerability

If you find a security issue, such as local file disclosure, arbitrary code
execution through an API endpoint, authentication bypass, unsafe tool
execution, or a security boundary failure, please **do not open a public
issue**.

Email: mahdijafarinajafabadi@gmail.com

Please include, when available:
- A concise description of the issue
- Affected commit, version, endpoint, or component
- Reproduction steps or a minimal proof of concept
- Potential security or privacy impact
- Any proposed mitigation

### Response targets

SIMORGH is a solo-maintained project, so these are targets rather than
contractual guarantees:

- Initial acknowledgement: within 7 calendar days
- Initial triage: within 14 calendar days
- Remediation target for confirmed high-severity issues: within 30 calendar days
- Public disclosure target: normally after a fix is available, or within 90
  calendar days after the initial report when coordinated disclosure is
  appropriate

Please do not publicly disclose an unpatched vulnerability before coordinated
handling has had a reasonable opportunity to protect users.

## Scope

This policy applies to the source code, workflows, release artifacts, and data
assets intentionally shipped from this repository.

It does **not** grant permission to probe private infrastructure, unpublished
data, accounts, or systems that are not explicitly part of the public SIMORGH
project.

## Security boundaries

SIMORGH is intended to remain offline-first and human-accountable. In
particular, security reports involving authentication boundaries, external
network access, local command/tool execution, memory access controls, secrets,
request-size limits, provenance controls, or release-gate bypasses are in
scope.

Do not include passwords, API tokens, private keys, or other live secrets in a
report. Redact them from logs and proof-of-concept material.
