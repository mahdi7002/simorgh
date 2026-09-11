from fastapi.testclient import TestClient
import main
from core.self_improvement_policy import ChangeRequest, RiskLevel, decision

def test_health_and_dashboard():
    c = TestClient(main.app)
    r = c.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'healthy'
    d = c.get('/dashboard/')
    assert d.status_code == 200

def test_personas():
    c = TestClient(main.app)
    r = c.get('/personas')
    assert r.status_code == 200
    assert len(r.json()['personas']) >= 3

def test_governance_boundaries():
    assert decision(ChangeRequest(RiskLevel.INFORMATIONAL)) == 'AUTO_ALLOWED'
    assert decision(ChangeRequest(RiskLevel.REVERSIBLE_STATE)) == 'AUTO_ALLOWED'
    assert decision(ChangeRequest(RiskLevel.EXECUTABLE_CHANGE)) == 'SANDBOX_AND_EVALUATE'
    assert decision(ChangeRequest(RiskLevel.PRIVILEGE_OR_NETWORK)) == 'HUMAN_GATE'
    assert decision(ChangeRequest(RiskLevel.CONSTITUTIONAL)) == 'HUMAN_GATE'
