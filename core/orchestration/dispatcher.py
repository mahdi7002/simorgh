from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DispatchResult:
    agents: list[str]
    reason: str


class Dispatcher:
    """
    Lightweight deterministic dispatcher.

    No autonomous model-selection is required for routing.
    This keeps routing cheap and predictable on low-RAM machines.
    """

    RULES = (
        (("شعر", "غزل", "مولوی", "حافظ", "شاعر", "poem", "poetry"), ("hafez",)),
        (("قرآن", "آیه", "اسلام", "دین", "quran"), ("hakim", "hafez")),
        (("چرا", "علت", "دلیل", "why"), ("hakim", "nazer")),
        (("چگونه", "چیکار", "انجام", "قدم", "how", "build", "code"), ("amel", "rahbar")),
        (("آموزش", "یاد", "توضیح", "teach"), ("moalem", "hakim")),
        (("داستان", "شعر", "خلق", "ایده", "story", "creative"), ("khaliq",)),
    )

    DEFAULT = ("hakim", "moalem")

    def dispatch(self, query: str, max_agents: int = 2) -> DispatchResult:
        q = (query or "").strip().lower()

        for keywords, agents in self.RULES:
            if any(k.lower() in q for k in keywords):
                return DispatchResult(list(agents[:max_agents]), "keyword-rule")

        return DispatchResult(list(self.DEFAULT[:max_agents]), "default-route")
