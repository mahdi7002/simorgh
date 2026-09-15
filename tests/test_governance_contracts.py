from core.orchestration.contracts import (
    ActionKind,
    ChangeProposal,
    EvidenceArtifact,
    GateDecision,
    Governance,
    RiskLevel,
)


def test_self_improvement_never_auto_allows():
    assert (
        Governance.decide(ActionKind.SELF_IMPROVE)
        is GateDecision.HUMAN_REQUIRED
    )
    assert (
        Governance.decide(ActionKind.SELF_IMPROVE, human_approved=True)
        is GateDecision.ALLOW
    )


def test_mutation_and_external_execution_require_human_gate():
    for action in (ActionKind.MUTATE, ActionKind.EXECUTE, ActionKind.EXTERNAL):
        assert Governance.decide(action) is GateDecision.HUMAN_REQUIRED
        assert Governance.decide(action, human_approved=True) is GateDecision.ALLOW


def test_local_read_can_be_allowed_without_provider():
    assert Governance.decide(ActionKind.READ) is GateDecision.ALLOW
    assert Governance.decide(ActionKind.EVIDENCE) is GateDecision.ALLOW


def test_critical_risk_requires_human():
    assert (
        Governance.decide(ActionKind.READ, risk=RiskLevel.CRITICAL)
        is GateDecision.HUMAN_REQUIRED
    )


def test_verified_evidence_requires_source_and_verified_flag():
    good = EvidenceArtifact(
        source="local:test",
        content="evidence",
        verified=True,
    )
    bad = EvidenceArtifact(
        source="",
        content="evidence",
        verified=True,
    )
    unverified = EvidenceArtifact(
        source="local:test",
        content="generated",
        verified=False,
    )

    assert Governance.verify_evidence(good)
    assert not Governance.verify_evidence(bad)
    assert not Governance.verify_evidence(unverified)


def test_change_proposal_cannot_apply_without_human_approval():
    proposal = ChangeProposal(
        proposal_id="test-001",
        summary="change a governed surface",
        target="core/example.py",
        action=ActionKind.MUTATE,
        risk=RiskLevel.HIGH,
        rationale="regression test",
    )

    assert not Governance.can_apply(proposal)
    assert Governance.can_apply(proposal, human_approved=True)


def test_change_proposal_serialization_is_explicit():
    proposal = ChangeProposal(
        proposal_id="test-002",
        summary="proposal only",
        target="docs/example.md",
        action=ActionKind.PROPOSE,
        risk=RiskLevel.LOW,
    )
    payload = proposal.as_dict()

    assert payload["action"] == "propose"
    assert payload["risk"] == "low"
    assert payload["evidence"] == []
