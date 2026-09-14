from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    warnings: list[str]
    checks: list[str]


class Reviewer:
    """
    Conservative quality boundary.

    This component never claims that generated text is true.
    For evidence-sensitive questions, missing evidence is a warning,
    even when the model itself uses words such as 'source', 'according to',
    'Quran', etc.
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
            or "حافظ" in q and "حافظه" not in q
        )

        has_real_evidence = bool(tool_results)

        if evidence_sensitive and not has_real_evidence:
            warnings.append("evidence_sensitive_request_without_tool_evidence")

        # تأییدِ سطحِ جمله: اگر شاهدِ واقعی داریم، حداقل بخشی از خودِ
        # متنِ بازیابی‌شده باید عیناً در پاسخِ پرسونا دیده بشه — وگرنه
        # یعنی پرسونا چیزی «شبیهِ» نقلِ قول ساخته، نه خودِ نقلِ قول را آورده.
        if evidence_sensitive and has_real_evidence:
            evidence_texts = [
                str(v) for v in tool_results.values() if v
            ] if isinstance(tool_results, dict) else [str(tool_results)]
            quoted_match = any(
                len(ev) > 15 and ev[:40] in combined
                for ev in evidence_texts
            )
            if not quoted_match:
                warnings.append("quoted_text_does_not_match_retrieved_evidence")

        # Generated prose saying "طبق منبع" is not evidence.
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
