# نقشه‌ی پورت‌های سیمرغ

| پورت | سرویس | مسیر اجرا | نوع پروسه |
|------|-------|-----------|-----------|
| 8080 | llama-server (gemma-3-4b) | ~/llama.cpp/build/bin/llama-server | systemd? یا دستی — نیاز به بررسی |
| 8000 | simorgh-core (main.py) | ~/simorgh/.venv/bin/python main.py | simorgh.service (systemd) |
| 8001 | persona server | ~/SimorghCore/persona_server.py | ناشناخته — نیاز به یکسان‌سازی (آیتم ۱ باتلاگ) |
| 8010 | Mother | ~/simorgh-mother-review/.venv/bin/python -m core.mother.server | simorgh-mother.service (systemd) |

آخرین به‌روزرسانی: بر اساس ممیزی ۲۷ سپتامبر ۲۰۲۶
