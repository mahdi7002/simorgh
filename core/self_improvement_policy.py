"""Deterministic governance boundary for SIMORGH self-improvement.

The model may propose improvements, but it may not expand its own authority.
This module is intentionally independent of the LLM prompt layer.
"""
from dataclasses import dataclass
from enum import IntEnum

class RiskLevel(IntEnum):
    INFORMATIONAL = 0
    REVERSIBLE_STATE = 1
    SANDBOX_ARTIFACT = 2
    EXECUTABLE_CHANGE = 3
    PRIVILEGE_OR_NETWORK = 4
    CONSTITUTIONAL = 5

@dataclass(frozen=True)
class ChangeRequest:
    risk: RiskLevel
    reversible: bool = True
    privilege_gain: bool = False
    policy_change: bool = False
    evaluator_change: bool = False
    rollback_available: bool = True

def decision(req: ChangeRequest) -> str:
    if req.risk >= RiskLevel.PRIVILEGE_OR_NETWORK or req.policy_change or req.evaluator_change or req.privilege_gain:
        return "HUMAN_GATE"
    if req.risk == RiskLevel.EXECUTABLE_CHANGE:
        return "SANDBOX_AND_EVALUATE"
    if not (req.reversible and req.rollback_available):
        return "HUMAN_GATE"
    return "AUTO_ALLOWED"
