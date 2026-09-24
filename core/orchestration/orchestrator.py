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

    @staticmethod
    def _format_evidence_answer(tool_results: dict) -> str:
        parts: list[str] = []
        for name, result in tool_results.items():
            if result.get("status") != "OK":
                continue
            data = result.get("data")
            if not data:
                continue

            if name == "poetry_search" and isinstance(data, list):
                for item in data[:3]:
                    if not isinstance(item, dict):
                        continue
                    poet = item.get("poet") or "شاعر نامشخص"
                    snippet = item.get("snippet") or ""
                    title = item.get("title") or ""
                    if snippet:
                        line = f'«{snippet}» — {poet}'
                        if title:
                            line += f' | اثر: {title}'
                        parts.append(line)
            elif name == "quran_search" and isinstance(data, list):
                for item in data[:3]:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text") or ""
                    if not text:
                        continue
                    ref = ""
                    if item.get("surah") and item.get("ayah"):
                        ref = f'سوره {item["surah"]}، آیه {item["ayah"]}'
                    parts.append(f'«{text}»' + (f' | {ref}' if ref else ""))
            else:
                parts.append(f"[TOOL:{name}] {data}")

        if not parts:
            return ""
        return "شواهد بازیابی‌شده از پایگاه دانش محلی:\n" + "\n".join(parts)

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

        # Evidence-sensitive requests use a deterministic database-first path.
        # A missing LLM must not turn a local knowledge lookup into a 30-60s timeout.
        if Reviewer.is_evidence_sensitive(query):
            evidence_answer = self._format_evidence_answer(board.tool_results)
            if evidence_answer:
                board.record_output("knowledge", evidence_answer, ai_generated=False)
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
                    "mode": "database-first",
                }
                state = board.as_dict()
                state["final_output"] = (
                    evidence_answer
                    if review.approved
                    else "[NOT_VERIFIED] شواهد بازیابی‌شده برای پاسخ تأیید نشد و نمایش داده نمی‌شود."
                )
                state["response_blocked"] = not review.approved
                return state

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
