# SIMORGH Mother

مادر سیمرغ یک لایهٔ ناظر و خودبازتاب است که بدون مالکیت بر هستهٔ HTTP، وضعیت سیستم، حافظهٔ زمانی، فعالیت‌ها، گزارش‌ها و مسیرهای پژوهش و کدنویسی را به‌صورت محلی نگه می‌دارد.

## اجزا

- core/mother/ledger.py: دفتر رویداد، boot، snapshot، گزارش، هدف، قرنطینه و اصلاحیه.
- core/mother/observer.py: مشاهدهٔ CPU، RAM، swap، disk، پردازش‌ها، پورت‌ها، systemd، Git و فایل‌های runtime.
- core/mother/reports.py: گزارش POST_BOOT، DAILY و WEEKLY و مقایسهٔ روزانه.
- core/mother/research.py: جست‌وجوی مرورگر و انتقال صریح URL به قرنطینه.
- core/mother/coding.py: پیشنهاد patch با مدل محلی، آزمون ایزوله و اعمال فقط پس از تأیید انسان.
- core/mother/quality.py: آزمون سلامت روزانه و ساخت proposal اصلاحی هنگام شکست.
- core/mother/service.py: observer دائمی بدون port.
- core/mother/api.py: API مادر.
- app/mother.html: نمای وب مادر و درگاه تحقیق.
- systemd/simorgh-mother.service.in: الگوی سرویس مستقل Mother.

## مرزها

ورودی اینترنتی مستقیماً دانش سیمرغ نیست. مسیر:

Browser Search
  -> URL
  -> safe fetch
  -> QUARANTINED
  -> optional local-model advisory review
  -> HUMAN APPROVAL
  -> provenance memory

متن وب «داده» است، نه دستور.

برای کد:

Local LLM
  -> patch proposal
  -> git apply --check
  -> isolated pytest
  -> VERIFIED / FAILED
  -> HUMAN APPROVAL
  -> working tree

Mother خودش commit یا push انجام نمی‌دهد.

## نصب سرویس مادر

این دستور فقط سرویس جدید Mother را نصب می‌کند و سرویس‌های دیگر SIMORGH را متوقف یا حذف نمی‌کند:

bash scripts/install-mother-service.sh

پس از نصب:

sudo systemctl status simorgh-mother.service --no-pager -l
sudo journalctl -u simorgh-mother.service -n 100 --no-pager

نمای وب:

http://127.0.0.1:8010/

دروازهٔ تحقیق تنها وقتی به اینترنت درخواست می‌فرستد که کاربر URL را صریحاً برای قرنطینه ارسال کند.

## خاموشی و بوت

Mother در هر بوت boot_id را ثبت می‌کند. اگر shutdown تمیز ثبت نشده باشد، گزارش بعدی آن را به‌عنوان وضعیت ناشناخته ثبت می‌کند و در بازهٔ خاموشی هیچ فعالیتی را حدس نمی‌زند.

## Godot

دادهٔ world_state.json در این مسیر قرار می‌گیرد:

~/.local/share/simorgh/mother/world_state.json

Godot می‌تواند این فایل یا /api/mother/state را برای نمایش تغییرات روزانه مصرف کند.
