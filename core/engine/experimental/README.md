# core/engine/experimental/

این ۲۲ فایل به هیچ‌جای مسیر زندهٔ برنامه (main.py, personas.py, core/chat.py) وصل
نیستند — نه مستقیم، نه غیرمستقیم. حسابرسی کامل با اسکریپت در ۲ سپتامبر ۲۰۲۶ انجام شد.

پنج فایل دیگر (`reflection.py`, `meta_reflection.py`, `truth.py`, `memory_graph.py`,
`stt.py`) در `core/engine/` باقی مانده‌اند چون واقعاً استفاده می‌شوند — نه در چت زنده،
بلکه توسط سه اسکریپت نگهداریِ سطح‌ریشه: `trigger_full_reflection.py`,
`import_knowledge.py`, `audio_converter.py`.

این فایل‌ها حذف نشده‌اند — فقط جابه‌جا شده‌اند تا مشخص باشد کدام‌ها واقعاً بخشی از
سیستم زنده‌اند و کدام‌ها طرح/اسکلت اولیه‌اند. اگر یکی از این‌ها را کامل و به main.py
وصل کردی، آن را از این پوشه به `core/engine/` برگردان.
