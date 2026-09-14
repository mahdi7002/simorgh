# SIMORGH Global Legal and Compliance Readiness Baseline

This document is a legal/compliance engineering baseline, not legal advice. It does not claim that SIMORGH is compliant with every jurisdiction or sector-specific law. A launch in a given country, market, or regulated domain requires jurisdiction- and use-case-specific legal review.

## Current project baseline

SIMORGH source code is released under the MIT License. The MIT license requires preservation of the copyright and license notice in copies or substantial portions of the software. It does not, by itself, license third-party dependencies, datasets, model weights, translations, music, images, or other assets. [1]

The repository currently contains local knowledge assets and SQLite databases, including `data/simorgh.db` and `data/simorgh_full.db`, plus cultural data. Their copyright, provenance, database rights, and redistribution terms are not established by the root MIT license. Treat these assets as **[NOT VERIFIED]** until each source is documented with provenance and applicable permission/license terms.

## Global baseline principles

The project should align its governance with the following baseline references:

- NIST AI RMF: risk management for trustworthy AI across design, development, deployment, and evaluation. [2]
- ISO/IEC 42001: an AI management system standard covering establishment, implementation, maintenance, and continual improvement of AI governance. [3]
- UNESCO Recommendation on the Ethics of AI: human rights, dignity, transparency, fairness, safety, privacy, and human oversight. [4]
- UN Global Digital Compact: responsible, accountable, transparent, human-centric AI governance with effective human oversight across the lifecycle. [5]
- SPDX/NTIA SBOM practice: machine-readable component, dependency, supplier, version, and license transparency. [6][7]

## EU readiness baseline

As of 2026-09-15, the EU AI Act is applicable, with some provisions phased in. Prohibited practices and AI literacy obligations have applied since 2025-02-02; GPAI obligations since 2025-08-02; the main Act became broadly applicable on 2026-08-02, with extended transition periods for certain high-risk systems. [8]

For the current SIMORGH scope, the strongest immediate requirements are governance, truthful capability communication, prohibited-use avoidance, AI interaction/content transparency where applicable, documentation, and risk management. Whether SIMORGH is a high-risk system depends on the actual use case and deployment context, not the repository name alone. [8]

The AI Act prohibits certain manipulative or deceptive AI practices and exploitation of vulnerabilities. SIMORGH's human-authority and anti-manipulation principles are directionally aligned, but alignment of intent is not proof of legal compliance. [9]

For GPAI, the EU Commission states obligations including technical documentation, a copyright policy, and a public summary of training content. SIMORGH is currently an application using local/provider models rather than a claim of providing a foundation model, so these provider obligations should not be attributed to SIMORGH unless its scope changes. [10]

## EU privacy baseline

GDPR requires appropriate technical and organizational safeguards, including data minimization, privacy by design/default, and security appropriate to risk. [11][12]

The EDPB's Opinion 28/2024 confirms that the lawfulness and anonymity of AI models involving personal data require case-by-case assessment, and that unlawful personal-data processing in model development can affect the lawfulness of continued or subsequent processing. [13]

SIMORGH therefore needs a documented data map covering memory, logs, imports, voice data, uploaded documents, model prompts, and optional external providers before a public service handles personal data at scale.

## EU product liability baseline

Directive (EU) 2024/2853 treats software, including AI systems, as products for its scope and applies to products placed on the market or put into service after 2026-12-09. It also addresses cybersecurity-related defects and software updates. Free/open-source software developed or supplied outside commercial activity has a specific exclusion, but commercial activity and later deployment can change the analysis. [14][15]

SIMORGH should therefore not rely on "open source" alone as a blanket liability shield.

## United States baseline

The U.S. does not currently provide one single federal AI statute covering every consumer AI use case. Sectoral, state, consumer-protection, privacy, copyright, product-liability, and contractual rules can apply.

The FTC continues to apply general consumer-protection principles to AI claims and has also proposed an AI-focused policy statement concerning deceptive practices and suppression of accuracy. Marketing statements about capability, safety, autonomy, privacy, or outcomes should therefore be evidence-bounded. [16]

Colorado's AI law, for example, imposes duties on developers and deployers of high-risk AI systems beginning 2026-02-01, including reasonable care against known or reasonably foreseeable algorithmic-discrimination risks and related documentation/impact-assessment duties. SIMORGH should not enter high-risk domains without a domain-specific compliance program. [17]

U.S. copyright status of AI outputs and training remains fact-specific. The U.S. Copyright Office states that AI-assisted outputs may be copyrightable where a human author determines sufficient expressive elements, while prompting alone is not sufficient. Training-data questions remain an active legal/policy area. [18][19]

## Copyright and data provenance gate

The repository root MIT license must not be treated as a license for embedded cultural datasets. Each distributable dataset should have:

1. source URL or archival source;
2. author/rights holder where known;
3. copyright/public-domain status by jurisdiction where material;
4. applicable license or permission;
5. translation rights separately identified;
6. database/sui-generis rights assessed where applicable;
7. required attribution and notice text;
8. restrictions such as non-commercial, share-alike, attribution, or access conditions;
9. a reproducible manifest tying every shipped asset to its source record.

Creative Commons itself recommends software-specific licenses for software, while CC licenses may be suitable for separate documentation or creative assets. [20]

## Security release gate

Before any internet-facing or hosted deployment, SIMORGH should require:

- loopback-only default;
- fail-closed behavior for external bind without explicit authentication;
- authentication tests for protected endpoints;
- HTTPS/TLS at the deployment edge;
- explicit CORS allowlist for hosted environments;
- request-size and upload limits;
- rate limiting where remotely exposed;
- safe error handling without path/token disclosure;
- dependency vulnerability scanning;
- SBOM generation;
- reproducible dependency/version records;
- incident-response and vulnerability disclosure procedures;
- no secrets in repository history or runtime defaults.

## Current technical findings

The current code has a fail-closed external-bind guard and token middleware in `main.py`. Loopback mode remains unauthenticated by design for local-only use; external bind requires `SIMORGH_KEY` and checks `x-token` on non-health requests. [21]

Authentication behavior is now regression-tested, along with fast/quality LLM timeouts, evidence gating, and the local sensor tool. The current full suite has passed locally at 32 tests before the latest authentication-boundary test extension; GitHub CI for the latest commit is the authoritative final check.

## Capability-claim gate

The project should keep its existing rule: IMPLEMENTED only when an executable implementation, regression test, and CI path exist. Everything else must remain EXPERIMENTAL, PLANNED, DISABLED, or [NOT VERIFIED]. This is particularly important for claims about autonomy, safety, privacy, memory ownership, tool calling, citations, or resistance to misuse.

## Release blockers

### P0 - must resolve before global public launch

- Dataset/content license and provenance manifest for all shipped data assets.
- Third-party dependency license inventory and SBOM.
- Public privacy/data-processing documentation describing memory, logs, imports, retention, deletion, export, and optional external providers.
- Domain/use-case policy defining prohibited and high-risk deployments.
- Security boundary tests and documented hosted deployment architecture.
- Legal review of commercial distribution and the jurisdictions actually targeted.

### P1 - resolve before broad consumer/hosted rollout

- Formal incident-response process and security contact SLA.
- Abuse/misuse test suite and red-team scenarios.
- Child-safety and age-appropriate controls if minors are in scope.
- Accessibility review for UI/API documentation.
- Model and dataset update/change-control records.
- Signed release artifacts and provenance where practical.

## Explicit non-claims

Passing the technical and documentation gates in this file does not mean "globally legally compliant." No single checklist can establish compliance in every country, sector, or deployment model. Compliance is a property of the concrete product, operator, processing activities, claims, users, jurisdictions, and commercial context.

## References

1. Open Source Initiative, The MIT License: https://opensource.org/license/mit
2. NIST, AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
3. ISO, ISO/IEC 42001:2023: https://www.iso.org/standard/42001
4. UNESCO, Recommendation on the Ethics of Artificial Intelligence: https://www.unesco.org/ethics-ai/en/recommendation
5. United Nations, Global Digital Compact: https://www.un.org/pact-for-the-future/en/annex-i-global-digital-compact
6. SPDX, Handling License Info: https://spdx.dev/learn/handling-license-info/
7. U.S. NTIA, Minimum Elements for an SBOM: https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom
8. European Commission, AI Act: https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
9. EUR-Lex, Regulation (EU) 2024/1689, Article 5: https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng
10. European Commission, GPAI obligations: https://digital-strategy.ec.europa.eu/en/factpages/general-purpose-ai-obligations-under-ai-act
11. EUR-Lex, GDPR Article 25: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CONSIL%3APE_17_2016_INIT
12. EUR-Lex, GDPR Article 32: https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1558176381563&uri=CELEX%3A32016R0679
13. EDPB, Opinion 28/2024 on AI models and personal data: https://www.edpb.europa.eu/documents/opinion-of-the-board-art-64/opinion-282024-on-certain-data-protection-aspects-related-to_en
14. EUR-Lex, Directive (EU) 2024/2853: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202402853
15. EUR-Lex, Directive 2024/2853, open-source software scope: https://eur-lex.europa.eu/legal-content/EN/TXT/?qid=1675017742161&uri=CELEX%3A32024L2853
16. FTC, Proposed AI accuracy/deception policy statement: https://www.ftc.gov/policy/public-comments/policy-statement-concerning-suppression-accuracy-artificial-intelligence-systems
17. Colorado General Assembly, SB24-205: https://leg.colorado.gov/bills/sb24-205
18. U.S. Copyright Office, AI and copyright: https://www.copyright.gov/policy/artificial-intelligence/
19. U.S. Copyright Office, Part 2: Copyrightability: https://www.copyright.gov/newsnet/2025/1060.html
20. Creative Commons FAQ: https://creativecommons.org/faq/
21. SIMORGH `main.py`: https://github.com/mahdi7002/simorgh/blob/main/main.py
