# SIMORGH Agent Fabric

## Decision

SIMORGH does **not** adopt Cursor, another agent vendor, or any cloud agent SDK as a core dependency.

The useful ideas observed in modern coding-agent systems are treated as architectural patterns only:

- durable task/run lifecycle;
- capability-based tool access;
- specialist workers/subagents;
- lifecycle hooks around tool execution;
- evidence artifacts rather than an opaque `done` claim.

SIMORGH implements these ideas under its own charter and keeps the execution layer provider-neutral.

## Governing boundary

The charter is the authority. In particular, automatic self-improvement is prohibited. No agent, subagent, model provider, tool, evaluator, or external service may silently modify SIMORGH's code, weights, capabilities, architecture, policy, permissions, or scope.

The core distinction is:

`Proposal != Command`

and the operational chain is:

`Question -> Read -> Evidence -> Propose -> Sandbox -> Evaluate -> Verify -> Human Gate -> Apply`

The `Apply` step is outside autonomous planning authority.

## Native contracts

`core/orchestration/contracts.py` defines small dependency-free contracts for:

- `ActionKind`: read, evidence, propose, execute, mutate, self-improve, external;
- `RiskLevel`: low through critical;
- `GateDecision`: allow, human-required, deny;
- `Capability`: what a worker may do and where it comes from;
- `EvidenceArtifact`: retrieved evidence plus provenance and verification state;
- `ChangeProposal`: explicit target, rationale, action, risk, and evidence;
- `Governance`: the authority boundary that decides whether an operation can proceed.

The governance layer deliberately does not execute actions. It is a gate, not an agent.

## Native runtime

`core/orchestration/runtime.py` now provides the dependency-free local control plane:

- `RunCoordinator` manages a small explicit run lifecycle;
- `AgentRun` records state without provider-owned persistence;
- `EvidencePack` keeps evidence, proposals, evaluations, verification, and human decision together;
- `ExecutionBoundary` separates sandbox preparation from application;
- `apply()` requires explicit human approval and a registered applier.

This runtime does not spawn a shell, call a cloud service, or modify the repository by itself.

## Provider adapters

Future providers may implement an adapter around these contracts. A Cursor adapter, local shell worker, remote API, MCP server, or another executor must not become a privileged path around `Governance`.

External execution is always an explicit capability and an explicit boundary. Networked providers are optional. The local provider remains the primary execution path.

## Evidence and provenance

Tool output is not automatically truth. A successful tool result is evidence only when it is actually returned by the tool and carries usable provenance. Generated text remains generated text.

Evidence artifacts are designed to be collected into an auditable evidence pack containing:

1. request/context;
2. retrieved evidence and provenance;
3. proposed actions;
4. risk and policy decision;
5. sandbox/evaluation results;
6. diff or artifact outputs;
7. verification results;
8. human decision.

## Subagents

Specialist workers are useful for decomposition, but they are not independent authorities. A researcher may retrieve evidence; a builder may prepare a patch; a verifier may challenge it. None may approve its own change.

This keeps the useful separation from agent frameworks while preserving SIMORGH's hierarchy:

`Human -> Governance -> Orchestrator -> Workers -> Tools`

not:

`Model -> Everything`

## Hooks

Lifecycle hooks are treated as policy interception points. Before any governed tool execution, the eventual adapter must make the requested capability, target, risk, provenance requirements, and approval state visible to the policy layer.

A hook must fail closed when the requested authority is not established.

## Memory boundary

Agent state, run state, evidence, and transient context are not automatically SIMORGH permanent memory. Memory mutation must pass the existing memory/governance rules and explicit user controls.

Provider conversation history, cloud session state, or external telemetry never becomes authoritative SIMORGH memory by accident.

## Current status

Provider-neutral contracts, the local run coordinator, evidence-pack model, execution boundary, and regression tests are implemented. Full multi-agent orchestration, MCP compatibility, external provider adapters, arbitrary sandbox executors, and provider-specific integrations remain separate implementation work and must not be marked `IMPLEMENTED` until executable code, regression tests, and CI coverage exist.
