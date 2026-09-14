# SIMORGH Prohibited and High-Risk Use Baseline

This policy is an engineering and product-safety baseline. It is not a complete legal policy and does not replace jurisdiction-specific law or professional advice.

## Prohibited uses for the general-purpose SIMORGH distribution

SIMORGH must not be configured or marketed to:

- manipulate people through covert or materially deceptive AI behavior;
- exploit known vulnerabilities of children or other vulnerable persons;
- impersonate a human without clear AI disclosure where required;
- make unsupported claims of medical, legal, financial, employment, educational, safety, or public-authority certainty;
- make decisions that secretly remove a person's meaningful human review or appeal path;
- silently mutate its own authority, policies, evaluators, permissions, or security controls;
- execute arbitrary shell commands as a model-directed tool capability;
- collect telemetry or personal data that is not necessary for a documented purpose;
- send user content to external providers unless that transfer is explicitly enabled and disclosed;
- package third-party or cultural content as MIT-licensed SIMORGH content unless its rights have been independently verified.

## High-risk deployment gate

Before deployment in healthcare, employment, education admissions/evaluation, credit/essential services, law enforcement, migration/border control, biometric categorisation, critical infrastructure, or other regulated/high-impact domains, the deployment owner must perform a jurisdiction-specific legal and risk assessment.

The repository's generic safeguards do not make a high-risk deployment compliant by themselves.

## Human authority rule

SIMORGH may propose. It may not silently acquire authority through configuration, memory mutation, tool expansion, evaluator changes, or privilege escalation.

## Transparency rule

Interactive AI output must be clearly identified to people where applicable. The API provides explicit AI-disclosure metadata and a machine-readable response header on generated-output endpoints; deployment UIs must render a clear user-facing disclosure.

## Enforcement model

Any violation discovered in testing, issue triage, or production monitoring is treated as a release-blocking product-safety finding until contained, understood, and addressed.
