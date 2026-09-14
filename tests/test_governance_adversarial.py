"""
تست خصمانه‌ی گاورننس (Charter Principle 16).
"""
import sqlite3

from core.engine import reflection, causal_discovery


def test_apply_proposals_never_auto_applies(tmp_path, monkeypatch):
    fake_proposals = [
        {
            "type": "blocks",
            "source": "تنبلی",
            "target": "موفقیت",
            "confidence": 0.99,
            "explanation": "کشف خودکار از ۵۰ پرسش مشابه",
            "knowledge_type": "hypothesis",
        }
    ]
    result = reflection.apply_proposals(fake_proposals)
    assert result is False


def test_apply_discoveries_never_auto_applies():
    fake_proposals = [
        {
            "source": "خشم",
            "target": "پشیمانی",
            "relation": "causes",
            "explanation": "کشف خودکار",
            "confidence": 0.95,
        }
    ]
    result = causal_discovery.apply_discoveries(fake_proposals)
    assert result == 0


def test_run_full_reflection_has_no_undefined_bypass():
    import inspect
    source = inspect.getsource(reflection.run_full_reflection)
    assert "apply_proposals(" not in source
