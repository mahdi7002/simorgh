import pytest

from core.orchestration.contracts import (
    ActionKind,
    ChangeProposal,
    EvidenceArtifact,
    RiskLevel,
)
from core.orchestration.runtime import EvidencePack, RunCoordinator, RunState


def proposal(action=ActionKind.MUTATE):
    return ChangeProposal(
        proposal_id="p-1",
        summary="test change",
        target="core/example.py",
        action=action,
        risk=RiskLevel.HIGH,
        rationale="test",
    )


def test_run_starts_with_local_evidence_pack():
    coordinator = RunCoordinator()
    run = coordinator.create("run-1", "request")

    assert run.state is RunState.CREATED
    assert isinstance(run.evidence_pack, EvidencePack)
    assert run.evidence_pack.request == "request"


def test_unverified_evidence_fails_closed():
    coordinator = RunCoordinator()
    coordinator.create("run-2", "request")

    accepted = coordinator.mark_evidence(
        "run-2",
        EvidenceArtifact(source="local:test", content="generated", verified=False),
    )

    assert accepted is False
    assert coordinator.runs["run-2"].state is RunState.FAILED


def test_verified_evidence_is_recorded():
    coordinator = RunCoordinator()
    coordinator.create("run-3", "request")

    accepted = coordinator.mark_evidence(
        "run-3",
        EvidenceArtifact(source="local:test", content="evidence", verified=True),
    )

    assert accepted is True
    run = coordinator.runs["run-3"]
    assert run.state is RunState.EVIDENCE
    assert len(run.evidence_pack.evidence) == 1


def test_sandbox_never_acts_as_approval():
    coordinator = RunCoordinator()
    observed = []
    applied = []
    coordinator.boundary.register_executor(
        "local",
        lambda item: observed.append(item.proposal_id) or "sandboxed",
        applier=lambda item: applied.append(item.proposal_id) or "applied",
    )

    result = coordinator.boundary.sandbox("local", proposal())

    assert result == "sandboxed"
    assert observed == ["p-1"]
    assert applied == []


def test_apply_requires_human_approval():
    coordinator = RunCoordinator()
    applied = []
    coordinator.boundary.register_executor(
        "local",
        lambda item: "sandboxed",
        applier=lambda item: applied.append(item.proposal_id) or "applied",
    )

    with pytest.raises(PermissionError):
        coordinator.boundary.apply("local", proposal())

    assert applied == []
    assert coordinator.boundary.apply("local", proposal(), human_approved=True) == "applied"
    assert applied == ["p-1"]


def test_external_proposal_still_requires_gate():
    coordinator = RunCoordinator()
    coordinator.boundary.register_executor("external", lambda item: "prepared", applier=lambda item: "applied")

    external = proposal(ActionKind.EXTERNAL)
    with pytest.raises(PermissionError):
        coordinator.boundary.apply("external", external)

    assert coordinator.boundary.apply("external", external, human_approved=True) == "applied"
