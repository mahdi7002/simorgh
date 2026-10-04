import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_eval", ROOT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)


def test_smalltalk_section_is_clean():
    r = run_eval.section_smalltalk()
    assert r["greetings_blocked"] == f"{len(run_eval.GREETING_CASES)}/{len(run_eval.GREETING_CASES)}"
    assert r["no_sources_on_greeting"] is True


def test_quran_section_is_seeded_and_reproducible():
    a, b = run_eval.section_quran(10, 7), run_eval.section_quran(10, 7)
    assert a == b and a["top10"] == "10/10"


def test_llm_section_scores_against_mock_endpoint(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"{}")

        def do_POST(self):
            n = int(self.headers["Content-Length"]); body = json.loads(self.rfile.read(n))
            q = body["messages"][-1]["content"]
            ans = "تهران" if "پایتخت" in q else "نمی‌دانم"
            out = json.dumps({"model": "mock", "choices": [{"message": {"content": ans}}], "usage": {"completion_tokens": 3}})
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(out.encode())

    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    qs = tmp_path / "q.json"
    qs.write_text(json.dumps({"items": [
        {"id": "a", "type": "qa", "prompt": "پایتخت ایران؟", "expected_any": ["تهران"]},
        {"id": "b", "type": "abstain", "prompt": "کتاب جعلی؟", "expected_any": ["نمی‌دانم"]},
        {"id": "c", "type": "qa", "prompt": "سؤال دیگر", "expected_any": ["شیراز"]},
    ]}, ensure_ascii=False), encoding="utf-8")
    try:
        res = run_eval.section_llm(f"http://127.0.0.1:{srv.server_port}/v1/chat/completions", qs, 10)
    finally:
        srv.shutdown()
        srv.server_close()
    assert res["model"] == "mock"
    assert res["by_type"] == {"qa": "1/2", "abstain": "1/1"}
