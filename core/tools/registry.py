from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable


@dataclass(frozen=True)
class ToolResult:
    tool: str
    status: str
    data: Any
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[[str], Any]] = {}
        self._provenance: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable[[str], Any],
        *,
        source: str,
    ) -> None:
        if not name or not callable(handler):
            raise ValueError("invalid tool registration")
        self._tools[name] = handler
        self._provenance[name] = {
            "source": source,
            "execution": "local",
        }

    def available(self, name: str) -> bool:
        return name in self._tools

    def execute(self, name: str, query: str) -> ToolResult:
        if name not in self._tools:
            return ToolResult(
                tool=name,
                status="NOT_AVAILABLE",
                data=None,
                provenance={
                    "source": "registry",
                    "execution": "local",
                },
            )

        try:
            data = self._tools[name](query)
            return ToolResult(
                tool=name,
                status="OK",
                data=data,
                provenance=dict(self._provenance[name]),
            )
        except Exception as exc:
            return ToolResult(
                tool=name,
                status="NOT_AVAILABLE",
                data=None,
                provenance={
                    **self._provenance[name],
                    "error_type": type(exc).__name__,
                },
            )

    def execute_many(
        self,
        names: list[str],
        query: str,
    ) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}

        for name in names:
            result = self.execute(name, query)
            results[name] = result.as_dict()

        return results


def build_default_registry() -> ToolRegistry:
    from core.book_search import get_book_wisdom
    from core.poetry_search import get_poetic_wisdom
    from core.quran_search import get_quran_wisdom
    from core.yazd_lore import format_for_prompt as format_yazd
    from core.tools.sensor_status import get_sensor_status

    registry = ToolRegistry()

    registry.register(
        "poetry_search",
        lambda query: get_poetic_wisdom(query, limit=2),
        source="core.poetry_search",
    )

    registry.register(
        "quran_search",
        lambda query: get_quran_wisdom(query, limit=3),
        source="core.quran_search",
    )

    registry.register(
        "book_search",
        lambda query: get_book_wisdom(query, limit=2),
        source="core.book_search",
    )

    registry.register(
        "yazd_lore",
        lambda query: format_yazd(query),
        source="core.yazd_lore",
    )

    registry.register(
        "sensor_status",
        get_sensor_status,
        source="core.tools.sensor_status",
    )

    return registry
