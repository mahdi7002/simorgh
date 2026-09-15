# SIMORGH public launch gate

This document is the internal/public-facing checklist for the first SIMORGH announcement. It is intentionally narrower than the long-term vision.

## Positioning

**SIMORGH is an open-source, offline-first experiment in human-accountable AI.**

Persian:

**هوش در خدمت انسان، نه انسان در خدمت هوش**

The central engineering question is:

> How capable can an AI system become while the human remains the owner and final authority?

SIMORGH should be presented as an experiment, not as AGI, a solved alignment system, or a competitor claim against frontier labs.

## Claims we can make

Only make claims supported by executable code, tests, and CI where applicable.

- Offline-first core exists.
- Local LLM support exists, but model availability is runtime-dependent.
- Twelve personas exist.
- Shared request blackboard, dispatcher and reviewer components exist.
- Provenance and governed self-improvement have regression coverage.
- Sentence-level citation verification is implemented and regression-tested.
- Automatic knowledge mutation is disabled behind human governance.

## Claims we must not make

- "SIMORGH is AGI."
- "SIMORGH cannot go rogue."
- "SIMORGH cannot be jailbroken or misused."
- "SIMORGH solves AI alignment."
- "SIMORGH is better than OpenAI/Anthropic/Google/xAI."
- "SIMORGH is fully autonomous."
- "SIMORGH has capabilities that have not been demonstrated."
- "SIMORGH is globally legally compliant without deployment-specific review."

## Release gate

Do not create the first public release until **all** of these are true:

### Engineering

- [ ] Main branch CI is green after the final documentation and code changes.
- [ ] A clean checkout can install the minimal dependency set.
- [ ] `import main` succeeds in a clean environment.
- [ ] Health endpoint succeeds.
- [ ] Persona endpoint succeeds and exposes all expected personas.
- [ ] Minimal demo passes its self-test without fabricating a fallback answer.
- [ ] Reviewer/citation verification regression tests pass.
- [ ] Governance/self-improvement regression tests pass.
- [ ] External-bind authentication tests pass.
- [ ] Voice/request size boundaries are tested.
- [ ] No secrets or API keys are present in tracked source/configuration.
- [ ] No unsupported capability is labelled IMPLEMENTED.

### Provenance, rights and compliance

- [ ] Core dependency SBOM is generated for the exact release environment.
- [ ] Third-party dependency licenses are verified for the exact shipped dependency scope.
- [ ] Every shipped data/model/content asset has an explicit provenance and redistribution basis.
- [ ] `compliance/ASSET_RIGHTS.csv` contains `VERIFIED` records for every shipped asset scope.
- [ ] Privacy/data-flow documentation matches executable behavior.
- [ ] Target jurisdiction review is complete for the intended deployment.
- [ ] High-risk/prohibited-use policy is reviewed.
- [ ] Security and vulnerability disclosure process is verified.

### Human authorization

- [ ] `compliance/RELEASE_SIGNOFF.md` is explicitly changed by the human maintainer to `APPROVED`.
- [ ] Target commit, version, reviewer and date are recorded in the signoff.
- [ ] Any open release-blocking PR or issue is resolved or explicitly accepted by the human maintainer.
- [ ] A version tag and GitHub Release are created only after the checks above.

A normal CI run may remain green while the compliance audit reports explicit **release blockers**. That is intentional: technical health and legal/human release authorization are different gates. The strict release workflow must remain blocked until the human signoff and all required evidence are complete.

## First demonstration

The strongest first demonstration is not a polished chatbot screenshot. It should show the control path:

`Question → Evidence retrieval → Provenance → Persona response → Reviewer → Citation verification → Human decision`

If evidence is unavailable, the system should say so rather than manufacture support.

## First public announcement

Recommended first post:

> I’ve been building something quietly.
>
> SIMORGH is an open-source experiment in human-accountable AI.
>
> Offline-first.  
> User-owned memory.  
> Provenance.  
> Bounded tools.  
> Human gates for self-improvement.
>
> Not a claim to have built AGI.
>
> A question turned into code:
>
> **How capable can an AI system become while the human remains the owner?**
>
> → https://github.com/mahdi7002/simorgh

Do not publish the announcement until the release gate is satisfied.

## Follow-up sequence

1. **Proposal ≠ Command**
2. **Known ≠ Inferred**
3. **Provenance > elegance**
4. Citation verification, with a concrete test/result
5. A runnable local demonstration
6. The human-directed development story
7. Limitations and failures discovered by users

The project should earn attention by showing evidence, not by inflating the claim.
