import importlib.util
import json
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_eval_paper", ROOT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)


def test_paper_benchmark_has_40_fixed_balanced_items():
    path = ROOT / "eval" / "questions_paper_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload["items"]
    counts = Counter(item["type"] for item in items)

    assert len(items) == 40
    assert counts == {
        "poetry_attribution": 10,
        "source_qa": 10,
        "abstain": 10,
        "classify": 10,
    }
    assert len({item["id"] for item in items}) == 40
    assert all(item.get("prompt") and item.get("expected_any") for item in items)
    assert all(item.get("source_ref") for item in items if item["type"] == "source_qa")


def test_classification_requires_exact_label_not_substring(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            json.loads(self.rfile.read(n))
            body = json.dumps({
                "model": "mock",
                "choices": [{"message": {"content": "زباله و روشنایی"}}],
                "usage": {"completion_tokens": 3},
            }, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    questions = tmp_path / "classify.json"
    questions.write_text(json.dumps({
        "items": [{
            "id": "test-label",
            "type": "classify",
            "prompt": "فقط یک برچسب",
            "expected_any": ["زباله"],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    try:
        result = run_eval.section_llm(
            f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            questions,
            timeout=5,
            use_retrieval=False,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert result["by_type"] == {"classify": "0/1"}


def test_retrieval_condition_passes_local_context_to_model(tmp_path, monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def do_POST(self):
            n = int(self.headers["Content-Length"])
            request = json.loads(self.rfile.read(n))
            received.append(request["messages"][-1]["content"])
            body = json.dumps({
                "model": "mock",
                "choices": [{"message": {"content": "سعدی"}}],
                "usage": {"completion_tokens": 1},
            }, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

    monkeypatch.setattr(
        run_eval,
        "local_retrieval_context",
        lambda prompt: {
            "context": "شاهد محلی: سعدی",
            "counts": {"quran": 0, "poetry": 1, "books": 0},
            "errors": [],
        },
    )
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    questions = tmp_path / "poetry.json"
    questions.write_text(json.dumps({
        "items": [{
            "id": "test-retrieval",
            "type": "poetry_attribution",
            "prompt": "این بیت از کیست؟",
            "expected_any": ["سعدی"],
        }]
    }, ensure_ascii=False), encoding="utf-8")
    try:
        result = run_eval.section_llm(
            f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            questions,
            timeout=5,
            use_retrieval=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert "شاهد محلی: سعدی" in received[0]
    assert result["by_type"] == {"poetry_attribution": "1/1"}
    assert result["retrieval_summary"]["items_with_context"] == 1
