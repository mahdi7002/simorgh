from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPlan:
    tools: list[str]
    reason: str


class ToolPlanner:
    """
    Cheap deterministic planner.

    Persona routing and source routing are deliberately separate.
    """

    POETRY = (
        "غزل",
        "شعر",
        "شاعر",
        "اشعار",
        "بیت",
        "حافظ",
        "مولوی",
        "سعدی",
        "فردوسی",
        "شعر",
        "poem",
        "poetry",
    )

    QURAN = (
        "قرآن",
        "قران",
        "آیه",
        "سوره",
        "تفسیر قرآن",
        "quran",
    )

    YAZD = (
        "یزد",
        "بادگیر دولت‌آباد",
        "قنات زارچ",
        "ساباط",
        "دوخواهران",
        "نارین قلعه",
        "چاپارخانه",
    )

    BOOK = (
        "کتاب",
        "کتابی",
        "منبع",
        "منابع",
        "دانش",
        "تاریخ",
        "فلسفه",
        "حکمت",
    )

    def plan(self, query: str) -> ToolPlan:
        q = (query or "").strip().lower()

        if not q:
            return ToolPlan([], "empty-query")

        tools: list[str] = []

        if any(x in q for x in self.POETRY):
            tools.append("poetry_search")

        if any(x in q for x in self.QURAN):
            tools.append("quran_search")

        if any(x in q for x in self.YAZD):
            tools.append("yazd_lore")

        if any(x in q for x in self.BOOK):
            tools.append("book_search")

        if tools:
            return ToolPlan(tools, "keyword-tool-plan")

        return ToolPlan([], "no-tool-required")
