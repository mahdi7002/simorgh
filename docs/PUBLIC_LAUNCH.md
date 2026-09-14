# SIMORGH public launch kit

This document defines the public-facing language for the first SIMORGH announcement. It is intentionally narrower than the project's long-term vision.

## Positioning

**SIMORGH is an open-source, offline-first experiment in human-accountable AI.**

Persian:

**سیمرغ، یک آزمایش متن‌باز و آفلاین‌محور برای ساخت هوش مصنوعی پاسخ‌گو به انسان است.**

Slogan:

**هوش در خدمت انسان، نه انسان در خدمت هوش**

## The question

> How capable can an AI system become while the human remains the owner and final authority?

This question is stronger than a claim such as “we built safe AGI” because it can be tested against code, policy, logs, regression tests, and actual behavior.

## Five things to show

1. **Offline-first**
   Run the minimal demo without an API key or cloud account.

2. **Proposal ≠ Command**
   Show that a proposed self-improvement action is not automatically an execution authorization.

3. **Known ≠ Inferred**
   Explain the distinction between evidence, user-provided information, and model inference.

4. **Provenance and verification**
   Show that evidence-sensitive answers are expected to carry evidence, and that sentence-level citation verification can reject mismatched quoted text.

5. **Human authority**
   Show the governance boundary around higher-risk self-improvement and automatic knowledge mutation.

## What not to claim

Do not describe SIMORGH as:

- AGI
- superintelligence
- “unhackable” or “cannot go rogue”
- a replacement for human judgment
- better than frontier models
- the world's first human-centered AI
- a fully autonomous agent

The public story should remain evidence-first. A limitation is useful information, not a marketing failure.

## First X post

```text
I’ve been building something quietly.

SIMORGH is an open-source experiment in human-accountable AI.

Offline-first.
User-owned memory.
Provenance.
Bounded tools.
Human gates for self-improvement.

Not a claim to have built AGI.

A question turned into code:

How capable can an AI system become while the human remains the owner?

→ https://github.com/mahdi7002/simorgh
```

## Follow-up sequence

### Post 2: Proposal ≠ Command

```text
One rule sits near the center of SIMORGH:

Proposal ≠ Command.

An AI system may suggest a change.
That suggestion is not permission to execute it.

For consequential self-improvement, the human remains the gate.

The interesting part is not the sentence.
It is making the boundary executable and testable.
```

### Post 3: Known ≠ Inferred

```text
Another rule:

Known ≠ Inferred.

Retrieved evidence, user-provided facts, and model inference should not silently become one undifferentiated “memory.”

SIMORGH treats provenance as part of the architecture, not decoration for the UI.
```

### Post 4: Verification

```text
A citation existing is not enough.

SIMORGH now checks whether quoted text actually matches the retrieved evidence, rather than merely checking that “some evidence” exists.

Small feature.
Important boundary.

Verification over claims.
```

### Post 5: Run it

```text
You don't have to trust the description.

Clone it.
Run the minimal demo.
Inspect the code.
Break it.

python3 demo/simorgh_minimal.py --test

If the claim and the behavior disagree, the behavior wins.
```

## Demo narrative

For a short video or screen recording, use this order:

1. Show the repository and README.
2. Run `python3 demo/simorgh_minimal.py --test`.
3. Run one Persian question and show the explicit execution mode.
4. Start the local service and call `/health` and `/personas`.
5. Show one governance test or reviewer regression test.
6. End on the sentence: **“The goal is not autonomous power. The goal is inspectable capability under human authority.”**

Do not use simulated screenshots or fabricated benchmark numbers.

## Release gate

Before creating `v0.1.0`, confirm all of the following:

- main branch CI is green
- minimal demo passes from a clean checkout
- full test suite passes
- README capability statuses still match executable code and tests
- no secrets or machine-specific paths are required
- release notes distinguish implemented, experimental, planned, and disabled behavior
- at least one real end-to-end demo is reproducible by a new user

Until these conditions are met, the repository should remain a project under active verification rather than being presented as a finished product.
