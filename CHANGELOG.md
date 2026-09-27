# تغییرات سیمرغ

## 2026-09-27
- ممیزی کامل سیستم: کشف و حذف یک ساب‌سیستم موازی متروکه (core/engine dead code, ~34 فایل)
- حذف سیستم پرسونای یتیم (personas.py/persona_chat.py)
- ساخت systemd unit برای Mother (قبلاً unsupervised بود)
- رفع باگ crash-loop روی پورت 8000 (پروسه‌ی دستی قدیمی)
- مستندسازی مرز دسترسی Mother (full روی simorgh، observe-only روی بقیه)
- تأیید ۱۶۰/۱۶۰ تست پس از پاکسازی
