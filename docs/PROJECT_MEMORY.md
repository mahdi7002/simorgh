# SIMORGH Project Memory
Verified: offline core, CI green, portable paths, soft optional imports, poetry fallback, provenance memory API methods.
Priority: wire /memory endpoints + contract tests; no Civilization scope until 5-min provenance demo works offline.

## پاکسازی ۲۷ سپتامبر ۲۰۲۶
یک ساب‌سیستم موازی و متروکه در core/engine/ (fast_router, understanding, why_engine,
agent_council, world_model, wisdom, و ۲۰ فایل مشابه در experimental/) حذف شد. این کد یک
دموی ژنریک دستیار خانه‌هوشمند بود (تلویزیون/کولر/پرینتر/فر)، هیچ ربطی به هویت فرهنگی
سیمرغ نداشت، مسیر LLM موازی و دور از حاکمیت پرسونا/منشور داشت، و صفر ارجاع خارجی در کل
ریپو داشت (تأیید شده با grep قبل از حذف). memory_graph.py نگه داشته شد چون توسط
import_knowledge.py و تست‌ها واقعاً استفاده می‌شه. personas.py/persona_chat.py (سیستم
پرسونای یتیم، جدا از core/chat.py زنده) نیز حذف شد.
