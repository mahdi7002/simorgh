# SIMORGH Global Jurisdiction Readiness Matrix

Status: planning and engineering control baseline. This is not a certification or legal opinion. Laws, guidance, enforcement priorities, exemptions, and applicability depend on the concrete product, deployment, users, data, sector, and jurisdiction.

| Jurisdiction / regime | Main trigger for SIMORGH | Engineering control | Current status | Release implication |
|---|---|---|---|---|
| European Union | AI Act, GDPR, ePrivacy and sector-specific rules | AI disclosure, human oversight, evidence discipline, privacy/data map, risk assessment, external-bind security | PARTIAL | P0 for hosted or regulated use |
| United Kingdom | UK GDPR / Data Protection Act framework and sector-specific rules | Privacy by design/default, DPIA where required, transparency, minimization, security | PARTIAL | P0 for hosted UK processing |
| United States | FTC consumer protection, state privacy/AI/product laws, sector rules | Evidence-bounded claims, no deceptive safety/autonomy claims, privacy/data inventory, domain risk controls | PARTIAL | P0 before commercial consumer deployment |
| California | CCPA/CPRA and 2025/2026 automated decisionmaking/cybersecurity rules where applicable | Data rights architecture, risk assessment readiness, opt-out/access/deletion flows for covered processing | PLANNED | P0 if covered California business processing occurs |
| Colorado | Colorado AI Act for high-risk systems, where applicable | Domain classification, impact/risk assessment, documentation, human oversight | NOT_IN_SCOPE_BY_DEFAULT | P0 before any high-risk deployment |
| Brazil | LGPD for personal-data processing | Purpose limitation, legal basis assessment, data-subject rights, security, transfers | PARTIAL | P0 for hosted Brazilian users |
| China | PIPL and related data/cybersecurity rules | Data minimization, purpose limitation, localization/transfer assessment, rights | NOT_VERIFIED | P0 before China launch |
| Japan | APPI | Purpose specification, security, transfers, rights and disclosures | NOT_VERIFIED | P0 before Japan launch |
| South Korea | PIPA | Personal-data governance, security, transfer and rights controls | NOT_VERIFIED | P0 before Korea launch |
| Singapore | PDPA | Notification/consent where applicable, purpose limitation, protection, accountability, breach process | PARTIAL | P0 before hosted launch |
| Australia | Privacy Act and sector-specific rules | Privacy impact/risk assessment, collection/use controls, security and breach readiness | NOT_VERIFIED | P0 before launch |

## Universal product rule

A global release is not one legal configuration. It is a collection of jurisdiction packs. A pack should define the market, user classes, data classes, purposes, legal bases or equivalent permissions, retention, transfer mechanism, age/child rules, high-risk domains, user rights, incident obligations, and customer-facing notices.

## Current evidence anchors

- EU AI Act transparency requirements apply from 2 August 2026 for relevant AI systems, including informing users when interacting with AI and certain marking/labelling requirements. See European Commission AI Act materials.
- EU GDPR requires data protection by design/default and security appropriate to risk.
- UK ICO guidance emphasizes data protection by design/default and AI-specific data protection assessment.
- California adopted 2026-effective regulations addressing, among other things, risk assessments, cybersecurity audits, and automated decisionmaking technology for covered businesses.
- Singapore PDPA imposes accountability, notification, consent/purpose limitation, and protection obligations.
- China PIPL regulates processing of natural persons' personal information in China.
- UNESCO's global AI ethics recommendation emphasizes human rights, safety, privacy, transparency, accountability, and human oversight.

## No automatic legal conclusion

A passing engineering test does not prove legal compliance. It provides evidence that a specific control exists. Applicability and legal sufficiency must be assessed for the actual deployment.
