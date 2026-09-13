from __future__ import annotations

from core.chat import ask
from .blackboard import Blackboard
from .dispatcher import Dispatcher
from .reviewer import Reviewer


class Orchestrator:
    def __init__(self) -> None:
        self.dispatcher = Dispatcher()
        self.reviewer = Reviewer()

    def run(self, query: str, max_agents: int = 2) -> dict:
        board = Blackboard(query=query)

        dispatch = self.dispatcher.dispatch(query, max_agents=max_agents)
        board.selected_agents = dispatch.agents

        for agent in dispatch.agents:
            try:
                result = ask(query, agent=agent)
                board.record_output(agent, result)
            except Exception as exc:
                board.record_output(
                    agent,
                    f"[NOT_AVAILABLE] persona {agent}: {type(exc).__name__}",
                )

        # Evidence is deliberately not invented here.
        # Until the selected persona tool adapters are exposed as a
        # first-class interface, the reviewer must see an empty evidence
        # set rather than pretending model output is tool evidence.
        review = self.reviewer.review(
            query=query,
            outputs=board.outputs,
            tool_results=board.tool_results,
        )

        board.review = {
            "approved": review.approved,
            "warnings": review.warnings,
            "checks": review.checks,
            "route_reason": dispatch.reason,
        }

        return board.as_dict()
