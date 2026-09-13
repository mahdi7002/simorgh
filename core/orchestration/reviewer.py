from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    warnings: list[str]
    checks: list[str]


class Reviewer:
    """
    Deterministic response-quality gate.

    It does not pretend to prove factual truth. It checks whether
    evidence-sensitive output contains enough provenance signals to
    deserve a normal answer path.
    """

    def review(self, query: str, outputs: dict[str, str], tool_results: dict) -> ReviewResult:
        warnings: list[str] = []
        checks = ["non_empty_output", "no_tool_claim_without_tool_result"]

        combined = "\n".join(v for v in outputs.values() if v)

        if not combined.strip():
            warnings.append("empty_response")

        evidence_words = (
            "بر اساس",
            "طبق",
            "آیه",
            "غزل",
            "بیت",
            "منبع",
            "source",
            "according to",
        )

        asks_for_source = any(
            x in (query or "").lower()
            for x in ("منبع", "دقیق", "آیه", "بیت", "source", "exact")
        )

        if asks_for_source and not tool_results and not any(
            x in combined for x in evidence_words
        ):
            warnings.append("evidence_sensitive_request_without_evidence")

        return ReviewResult(
            approved=not warnings,
            warnings=warnings,
            checks=checks,
        )
