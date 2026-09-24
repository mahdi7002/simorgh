from __future__ import annotations

import argparse
import importlib
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_no}: each JSONL row must be an object")
        if "q" not in item:
            raise ValueError(f"{path}:{line_no}: missing required field 'q'")
        cases.append(item)
    return cases


def load_callable(spec: str) -> Callable[[str], Any]:
    try:
        module_name, function_name = spec.rsplit(":", 1)
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
    except (ValueError, ImportError, AttributeError) as exc:
        raise SystemExit(f"invalid callable '{spec}': {exc}") from exc
    if not callable(function):
        raise SystemExit(f"'{spec}' is not callable")
    return function


def normalize(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        status = str(raw.get("status", "")).lower()
        poet = raw.get("poet")
        candidates = raw.get("candidates") or []
        if isinstance(candidates, str):
            candidates = [candidates]
        return {
            "status": status,
            "poet": poet,
            "candidates": list(candidates) if isinstance(candidates, (list, tuple)) else [],
            "raw": raw,
        }

    if isinstance(raw, list):
        first = raw[0] if raw else {}
        return {
            "status": "answer" if raw else "not_found",
            "poet": first.get("poet") if isinstance(first, dict) else None,
            "candidates": [],
            "raw": raw,
        }

    return {
        "status": "answer" if raw else "not_found",
        "poet": None,
        "candidates": [],
        "raw": raw,
    }


def evaluate(
    cases: list[dict[str, Any]],
    function: Callable[[str], Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    known = answered = correct = 0
    false_positive = 0
    abstained_known = 0

    per_case_ms: list[float] = []

    for case in cases:
        case_started = time.perf_counter()
        raw = function(str(case["q"]))
        per_case_ms.append((time.perf_counter() - case_started) * 1000)
        result = normalize(raw)

        expected_poet = case.get("poet")
        expected_status = str(case.get("status", "")).lower()
        is_negative = bool(
            case.get("must_not_answer")
            or expected_status in {"not_found", "uncertain", "abstain"}
        )

        if expected_poet:
            known += 1

        if result["status"] in {"answer", "ok"}:
            answered += 1
            if is_negative:
                false_positive += 1

        poet_match = bool(
            expected_poet
            and result["poet"]
            and str(result["poet"]).strip() == str(expected_poet).strip()
        )

        if expected_poet and poet_match:
            correct += 1

        if expected_poet and not poet_match:
            candidates = {str(x).strip() for x in result["candidates"]}
            if str(expected_poet).strip() in candidates:
                pass
            elif result["status"] not in {"answer", "ok"}:
                abstained_known += 1

        rows.append(
            {
                "id": case.get("id"),
                "q": case["q"],
                "expected_poet": expected_poet,
                "expected_status": expected_status,
                "result": result,
                "latency_ms": round(per_case_ms[-1], 3),
            }
        )

    elapsed = time.perf_counter() - started
    answered_known = sum(
        1
        for row in rows
        if row["expected_poet"]
        and row["result"]["status"] in {"answer", "ok"}
    )

    return {
        "cases": len(cases),
        "known_cases": known,
        "answered_cases": answered,
        "answered_known_cases": answered_known,
        "correct_known_answers": correct,
        "coverage": round(answered_known / known, 4) if known else 0.0,
        "accuracy_on_known_answers": round(correct / answered_known, 4)
        if answered_known
        else 0.0,
        "false_positive_count": false_positive,
        "false_positive_rate": round(false_positive / len(cases), 4) if cases else 0.0,
        "abstained_known_cases": abstained_known,
        "elapsed_seconds": round(elapsed, 6),
        "latency_ms_mean": round((elapsed / len(cases)) * 1000, 3) if cases else 0.0,
        "latency_ms_median": round(statistics.median(per_case_ms), 3) if per_case_ms else 0.0,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generic JSONL knowledge evaluator")
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument(
        "--callable",
        required=True,
        help="Python callable in module:function form; it receives one query string",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    function = load_callable(args.callable)
    report = evaluate(cases, function)

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
