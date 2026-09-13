from dataclasses import dataclass, field
from typing import Any


@dataclass
class Blackboard:
    query: str
    selected_agents: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    tool_results: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)

    def record_output(self, agent: str, output: str) -> None:
        self.outputs[agent] = output

    def record_tool_result(self, name: str, result: Any) -> None:
        self.tool_results[name] = result

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "selected_agents": list(self.selected_agents),
            "outputs": dict(self.outputs),
            "tool_results": dict(self.tool_results),
            "review": dict(self.review),
        }
