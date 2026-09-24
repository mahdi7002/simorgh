from __future__ import annotations

from core.chat import PERSONAS, ask
from core.tools import build_default_registry, ToolPlanner
from .blackboard import Blackboard
from .dispatcher import Dispatcher
from .reviewer import Reviewer


class Orchestrator:
    def __init__(self) -> None:
        self.dispatcher = Dispatcher()
        self.reviewer = Reviewer()
        self.tools = build_default_registry()
        self.tool_planner = ToolPlanner()

    @staticmethod
    def _format_tool_context(tool_results: dict) -> str:
        parts: list[str] = []

        for name, result in tool_results.items():
            if result.get("status") != "OK":
                continue

            data = result.get("data")
            if not data:
                continue

            parts.append(
                f"[TOOL:{name}]\n"
                f"{data}"
            )

        return "\n\n".join(parts)

    def run(self, query: str, max_agents: int = 2) -> dict:
        board = Blackboard(query=query)

        dispatch = self.dispatcher.dispatch(query, max_agents=max_agents)
        board.selected_agents = dispatch.agents

        plan = self.tool_planner.plan(query)

        if plan.tools:
            board.tool_results = self.tools.execute_many(
                plan.tools,
                query,
            )

        tool_context = self._format_tool_context(board.tool_results)

        for agent in dispatch.agents:
            try:
                result, ai_generated = ask(
                    query,
                    agent=agent,
                    tool_context=tool_context,
                    use_builtin_tools=False,
                    return_metadata=True,
                )
                board.record_output(agent, result, ai_generated=ai_generated)
            except Exception as exc:
                board.record_output(
                    agent,
                    f"[NOT_AVAILABLE] persona {agent}: {type(exc).__name__}",
                    ai_generated=False,
                )

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
            "tool_plan_reason": plan.reason,
        }

        # The review result is a real boundary, not a diagnostic hint.  Keep
        # raw agent outputs available for local audit, but expose a safe final
        # answer only when the reviewer approves the assembled response.
        state = board.as_dict()
        combined_response = "\\n\\n".join(
            f"[{agent}]\\n{text}"
            for agent, text in board.outputs.items()
            if text
        )
        state["final_output"] = (
            combined_response
            if review.approved
            else "[NOT_VERIFIED] پاسخ به دلیل نبود شواهد کافی تأیید نشد و نمایش داده نمی‌شود."
        )
        state["response_blocked"] = not review.approved
        return state
