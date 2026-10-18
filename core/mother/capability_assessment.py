from __future__ import annotations
from typing import Any

CAPABILITIES: tuple[dict[str, Any], ...] = (
    {"operation":"discover","human_value":"HIGH","helps_human":True,"cost":"LOW","risk":"LOW","purpose":"Find real project/repository boundaries without changing source."},
    {"operation":"inspect_git","human_value":"HIGH","helps_human":True,"cost":"LOW","risk":"LOW","purpose":"Expose branch, HEAD, dirty state, refs and recoverable source state."},
    {"operation":"read_source","human_value":"HIGH","helps_human":True,"cost":"MEDIUM","risk":"MEDIUM","purpose":"Read relevant source/configuration to explain behavior."},
    {"operation":"verify","human_value":"HIGH","helps_human":True,"cost":"MEDIUM","risk":"LOW","purpose":"Run declared safe tests/checks and preserve evidence."},
    {"operation":"snapshot","human_value":"HIGH","helps_human":True,"cost":"MEDIUM/HIGH","risk":"LOW","purpose":"Preserve enough workspace state to recover it."},
    {"operation":"repair","human_value":"CONDITIONAL","helps_human":True,"cost":"MEDIUM/HIGH","risk":"HIGH","purpose":"Repair a diagnosed failure after backup and explicit permission."},
    {"operation":"execute_arbitrary","human_value":"LOW_BY_DEFAULT","helps_human":False,"cost":"UNKNOWN","risk":"VERY_HIGH","purpose":"Run arbitrary discovered commands without a verification contract."},
    {"operation":"install_dependencies","human_value":"CONDITIONAL","helps_human":True,"cost":"MEDIUM/HIGH","risk":"MEDIUM/HIGH","purpose":"Prepare a declared environment when explicitly authorized."},
    {"operation":"cloud_workspace","human_value":"CONDITIONAL","helps_human":True,"cost":"MEDIUM/HIGH","risk":"MEDIUM","purpose":"Provision an optional remote execution environment."},
    {"operation":"telemetry","human_value":"LOW_BY_DEFAULT","helps_human":False,"cost":"MEDIUM","risk":"HIGH","purpose":"Send workspace information to third parties; disabled by default."},
)

def capability_map() -> list[dict[str, Any]]:
    return [dict(x) for x in CAPABILITIES]
