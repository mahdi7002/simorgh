from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ActionKind(str, Enum):
    READ = "read"
    EVIDENCE = "evidence"
    PROPOSE = "propose"
    EXECUTE = "execute"
    MUTATE = "mutate"
    SELF_IMPROVE = "self_improve"
    EXTERNAL = "external"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateDecision(str, Enum):
    ALLOW = "allow"
    HUMAN_REQUIRED = "human_required"
    DENY = "deny"


@dataclass(frozen=True)
class Capability:
    name: str
    actions: frozenset[ActionKind]
    source: str = "local"
    external: bool = False

    def permits(self, action: ActionKind) -> bool:
        return action in self.actions


@dataclass(frozen=True)
class EvidenceArtifact:
    source: str
    content: Any
    verified: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChangeProposal:
    proposal_id: str
    summary: str
    target: str
    action: ActionKind
    risk: RiskLevel
    rationale: str
    evidence: tuple[EvidenceArtifact, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["risk"] = self.risk.value
        data["evidence"] = [item.as_dict() for item in self.evidence]
        return data


class Governance:
    """Provider-neutral authority boundary for SIMORGH.

    This class only decides whether an operation may proceed. It never executes
    the requested action and never changes code, configuration, memory policy,
    evaluators, permissions, or model weights.
    """

    @staticmethod
    def decide(
        action: ActionKind,
        *,
        risk: RiskLevel = RiskLevel.LOW,
        external: bool = False,
        human_approved: bool = False,
    ) -> GateDecision:
        if action is ActionKind.SELF_IMPROVE:
            return GateDecision.ALLOW if human_approved else GateDecision.HUMAN_REQUIRED

        if action in {ActionKind.MUTATE, ActionKind.EXECUTE, ActionKind.EXTERNAL}:
            return GateDecision.ALLOW if human_approved else GateDecision.HUMAN_REQUIRED

        if external:
            return GateDecision.ALLOW if human_approved else GateDecision.HUMAN_REQUIRED

        if risk is RiskLevel.CRITICAL:
            return GateDecision.HUMAN_REQUIRED

        return GateDecision.ALLOW

    @staticmethod
    def verify_evidence(artifact: EvidenceArtifact) -> bool:
        return artifact.verified and bool(artifact.source)

    @staticmethod
    def can_apply(proposal: ChangeProposal, *, human_approved: bool = False) -> bool:
        decision = Governance.decide(
            proposal.action,
            risk=proposal.risk,
            external=False,
            human_approved=human_approved,
        )
        return decision is GateDecision.ALLOW
