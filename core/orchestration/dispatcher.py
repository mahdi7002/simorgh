from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DispatchResult:
    agents: list[str]
    reason: str


class Dispatcher:
    """
    Cheap deterministic routing for low-resource environments.

    Important:
    substring collisions such as حافظ داخل حافظه must not select hafez.
    """

    RULES = (
        (
            ("غزل", "مولوی", "شاعر", "اشعار", "poem", "poetry"),
            ("hafez",),
        ),
        (
            ("قرآن", "آیه", "اسلام", "quran"),
            ("hakim", "hafez"),
        ),
        (
            ("چرا", "علت", "دلیل", "why"),
            ("hakim", "nazer"),
        ),
        (
            ("چگونه", "چیکار کنم", "انجام بده", "قدم بعدی", "how", "build", "code"),
            ("amel", "rahbar"),
        ),
        (
            ("آموزش", "یاد بده", "توضیح بده", "teach"),
            ("moalem", "hakim"),
        ),
        (
            ("داستان", "قصه", "ایده", "خلاق", "story", "creative"),
            ("khaliq",),
        ),
    )

    DEFAULT = ("hakim", "moalem")

    def dispatch(self, query: str, max_agents: int = 2) -> DispatchResult:
        q = (query or "").strip().lower()

        if not q:
            return DispatchResult(list(self.DEFAULT[:max_agents]), "default-route")

        # حافظه is not حافظ.
        # Prevent Persian substring collision.
        if "حافظه" in q:
            return DispatchResult(["hakim", "nazer"][:max_agents], "memory-topic")

        for keywords, agents in self.RULES:
            if any(keyword in q for keyword in keywords):
                return DispatchResult(list(agents[:max_agents]), "keyword-rule")

        return DispatchResult(list(self.DEFAULT[:max_agents]), "default-route")
