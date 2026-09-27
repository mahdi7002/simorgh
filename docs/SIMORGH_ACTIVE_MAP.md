# SIMORGH ACTIVE MAP

## Purpose

SIMORGH Active Map is the read-only operational map of the repository and runtime.

It is intended to make the system observable before changes are proposed.

The Map does not replace governance and does not certify correctness.

## Core Loop

SEE -> UNDERSTAND -> MEASURE -> TEST -> ATTACK -> PROPOSE -> HUMAN GATE -> CHANGE -> VERIFY -> RECORD -> SEE

The important boundary is:

Agent -> Proposal -> Governance -> Human Gate -> Action

An agent must not silently mutate the system.

## Arenas

1. CODE ARENA
2. KNOWLEDGE ARENA
3. MODEL ARENA
4. GOVERNANCE ARENA
5. SIMULATION ARENA
6. RUNTIME ARENA
7. RELEASE ARENA

## Evidence Principles

- KNOWN != INFERRED
- COVERED != VERIFIED
- PROVENANCE > elegance
- UNKNOWN must remain UNKNOWN
- Missing evidence must not become a positive claim
- The Map must show the evidence behind an assertion whenever possible

## Status Vocabulary

- UNKNOWN
- DISCOVERED
- PLANNED
- EXPERIMENTAL
- IMPLEMENTED
- COVERED
- VERIFIED
- BLOCKED
- CONFLICT
- DISABLED
- DEPRECATED

## Verification Boundary

The initial Active Map scanner is deliberately conservative.

It can discover repository structure, source files, tests, model artifacts, selected capabilities, Git state, runtime indicators, and textual governance signals.

It cannot prove that code is correct merely because a file exists or a test exists.

Therefore:

COVERED != VERIFIED

The scanner currently reports verified count as zero unless an explicit verification mechanism exists.

## M-0708ee

Mission M-0708ee is the first concrete loop example.

Its initial evidence is the repository test:

`tests/test_core_paths.py`

The corresponding commit is:

`d16ce4c`

This mission demonstrates the intended progression from a discovered test artifact toward measurable verification.

## Read-Only Rule

The initial scanner must not:

- modify application source code
- modify databases
- install packages
- change Git history
- commit
- push
- silently change runtime configuration

Its generated map is an observation artifact.

## Current Scope

Version 1 focuses on repository discovery and evidence collection.

Future versions can add:

- dependency graph
- capability graph
- mission graph
- runtime health graph
- model inventory
- knowledge-source graph
- governance evidence graph
- release evidence
- experiment results
- human approval records

## Design Principle

The City is not merely a dashboard.

It is intended to become the operational ground where SIMORGH can observe, test, repair, evaluate, govern, and record the state of the system.

The first requirement is visibility.

The second is evidence.

The third is controlled action.
