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

## Release gate

Do not create the first public release until all of these are true:

- [ ] Main branch CI is green after the final documentation and code changes.
- [ ] A clean checkout can install the minimal dependency set.
- [ ] `import main` succeeds in a clean environment.
- [ ] Health endpoint succeeds.
- [ ] Persona endpoint succeeds and exposes all expected personas.
- [ ] Minimal demo passes its self-test.
- [ ] Reviewer/citation verification regression tests pass.
- [ ] Governance/self-improvement regression tests pass.
- [ ] No secrets or API keys are present in tracked source/configuration.
- [ ] No unsupported capability is labelled IMPLEMENTED.
- [ ] Release notes explicitly state runtime-dependent limitations.
- [ ] A version tag and GitHub Release are created only after the checks above.

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
