from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    warnings: list[str]
    checks: list[str]


class Reviewer:
    """
    Conservative quality boundary.

    This component never claims that generated text is true.
    For evidence-sensitive questions, only successful tool results that
    actually contain data count as evidence.
    """

    EVIDENCE_REQUESTS = (
        "منبع",
        "منابع",
        "دقیق",
        "آیه",
        "بیت",
        "غزل",
        "نقل",
        "source",
        "exact",
        "citation",
    )

    @staticmethod
    def _successful_evidence(tool_results: dict[str, Any]) -> list[str]:
        fragments: list[str] = []
        if not isinstance(tool_results, dict):
            return fragments

        for result in tool_results.values():
            if not isinstance(result, dict):
                continue
            if result.get("status") != "OK":
                continue
            data = result.get("data")
            if data is None or data == "" or data == [] or data == {}:
                continue
            fragments.append(str(data))
        return fragments

    def review(
        self,
        query: str,
        outputs: dict[str, str],
        tool_results: dict,
    ) -> ReviewResult:
        warnings: list[str] = []
        checks = [
            "non_empty_output",
            "evidence_gate",
            "no_false_evidence_claim",
            "quoted_text_matches_evidence",
        ]

        combined = "\n".join(v for v in outputs.values() if v).strip()

        if not combined:
            warnings.append("empty_response")

        q = (query or "").lower()

        evidence_sensitive = (
            any(word in q for word in self.EVIDENCE_REQUESTS)
            or "قرآن" in q
            or "آیه" in q
            or "شعر" in q
            or "غزل" in q
            or "مولوی" in q
            or ("حافظ" in q and "حافظه" not in q)
        )

        evidence_fragments = self._successful_evidence(tool_results)
        has_real_evidence = bool(evidence_fragments)

        if evidence_sensitive and not has_real_evidence:
            warnings.append("evidence_sensitive_request_without_tool_evidence")

        if evidence_sensitive and has_real_evidence:
            # Tool data may be structured rather than plain quoted text.
            # We only flag a mismatch when a substantial literal fragment
            # should reasonably be present but none is visible in the output.
            quoted_match = any(
                len(fragment) > 15 and fragment[:40] in combined
                for fragment in evidence_fragments
            )
            if not quoted_match:
                warnings.append("quoted_text_does_not_match_retrieved_evidence")

        if not has_real_evidence:
            generated_claim_markers = (
                "طبق منابع",
                "بر اساس منبع",
                "بر اساس قرآن",
                "طبق قرآن",
                "مطابق منبع",
                "according to sources",
            )
            if any(marker in combined.lower() for marker in generated_claim_markers):
                warnings.append("generated_evidence_claim_without_evidence")

        return ReviewResult(
            approved=not warnings,
            warnings=warnings,
            checks=checks,
        )
