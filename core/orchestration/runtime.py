from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .contracts import ChangeProposal, EvidenceArtifact, GateDecision, Governance


class RunState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    EVIDENCE = "evidence"
    PROPOSED = "proposed"
    SANDBOXED = "sandboxed"
    EVALUATED = "evaluated"
    VERIFIED = "verified"
    HUMAN_PENDING = "human_pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class EvidencePack:
    request: str
    evidence: list[EvidenceArtifact] = field(default_factory=list)
    proposals: list[ChangeProposal] = field(default_factory=list)
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    verification: list[dict[str, Any]] = field(default_factory=list)
    human_decision: str | None = None

    def add_evidence(self, artifact: EvidenceArtifact) -> None:
        self.evidence.append(artifact)

    def add_proposal(self, proposal: ChangeProposal) -> None:
        self.proposals.append(proposal)

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "evidence": [item.as_dict() for item in self.evidence],
            "proposals": [item.as_dict() for item in self.proposals],
            "evaluations": list(self.evaluations),
            "verification": list(self.verification),
            "human_decision": self.human_decision,
        }


@dataclass
class AgentRun:
    run_id: str
    request: str
    state: RunState = RunState.CREATED
    evidence_pack: EvidencePack | None = None
    result: Any = None
    error: str | None = None

    def transition(self, state: RunState) -> None:
        self.state = state


class ExecutionBoundary:
    """Provider-neutral boundary separating proposal from actual mutation.

    Executors may observe a proposal and prepare a sandbox result, but only
    ``apply`` with an explicit human approval can perform the supplied action.
    No model or provider object is trusted as an authority.
    """

    def __init__(self) -> None:
        self._executors: dict[str, Callable[[ChangeProposal], Any]] = {}
        self._appliers: dict[str, Callable[[ChangeProposal], Any]] = {}

    def register_executor(
        self,
        name: str,
        executor: Callable[[ChangeProposal], Any],
        *,
        applier: Callable[[ChangeProposal], Any] | None = None,
    ) -> None:
        if not name or not callable(executor):
            raise ValueError("invalid executor registration")
        self._executors[name] = executor
        if applier is not None:
            if not callable(applier):
                raise ValueError("invalid applier registration")
            self._appliers[name] = applier

    def sandbox(self, name: str, proposal: ChangeProposal) -> Any:
        executor = self._executors.get(name)
        if executor is None:
            raise KeyError(name)
        return executor(proposal)

    def apply(
        self,
        name: str,
        proposal: ChangeProposal,
        *,
        human_approved: bool = False,
    ) -> Any:
        if not Governance.can_apply(proposal, human_approved=human_approved):
            raise PermissionError("human approval required before apply")
        applier = self._appliers.get(name)
        if applier is None:
            raise KeyError(f"no applier registered for {name}")
        return applier(proposal)


class RunCoordinator:
    """Small local lifecycle coordinator; no cloud/provider dependency."""

    def __init__(self) -> None:
        self.boundary = ExecutionBoundary()
        self.runs: dict[str, AgentRun] = {}

    def create(self, run_id: str, request: str) -> AgentRun:
        if run_id in self.runs:
            raise ValueError(f"run already exists: {run_id}")
        run = AgentRun(run_id=run_id, request=request)
        run.evidence_pack = EvidencePack(request=request)
        self.runs[run_id] = run
        return run

    def propose(self, run_id: str, proposal: ChangeProposal) -> None:
        run = self._get(run_id)
        if run.evidence_pack is None:
            raise RuntimeError("evidence pack missing")
        run.evidence_pack.add_proposal(proposal)
        run.transition(RunState.PROPOSED)

    def mark_evidence(self, run_id: str, artifact: EvidenceArtifact) -> bool:
        run = self._get(run_id)
        if run.evidence_pack is None:
            raise RuntimeError("evidence pack missing")
        if not Governance.verify_evidence(artifact):
            run.transition(RunState.FAILED)
            return False
        run.evidence_pack.add_evidence(artifact)
        run.transition(RunState.EVIDENCE)
        return True

    def request_human_gate(self, run_id: str) -> None:
        run = self._get(run_id)
        run.transition(RunState.HUMAN_PENDING)

    def decide(self, run_id: str, approved: bool) -> None:
        run = self._get(run_id)
        if run.evidence_pack is None:
            raise RuntimeError("evidence pack missing")
        run.evidence_pack.human_decision = "approved" if approved else "rejected"
        run.transition(RunState.VERIFIED if approved else RunState.REJECTED)

    def _get(self, run_id: str) -> AgentRun:
        try:
            return self.runs[run_id]
        except KeyError as exc:
            raise KeyError(f"unknown run: {run_id}") from exc
