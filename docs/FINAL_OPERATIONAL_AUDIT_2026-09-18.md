# گزارش ممیزی عملیاتی نهایی سیمرغ
## 2026-09-18

این سند گزارش «آنچه واقعاً اجرا و مشاهده شد» است، نه فهرست ادعاهای معماری. هرجا آزمایش مستقیم انجام نشده، عمداً با برچسب **[NOT VERIFIED]** یا **[NOT AVAILABLE]** ثبت شده است.

## 1. دامنهٔ پذیرش

هدف این دور، بستن مسیر اجرای کاربر عادی روی Linux و اطمینان از این موارد بود:

- مخزن محلی با `origin/main` یکسان باشد.
- تست‌های regression سبز باشند.
- Python runtime واقعی پروژه استفاده شود.
- هسته با systemd user service به‌صورت دائمی اجرا شود.
- بعد از crash خودکار برگردد.
- بعد از خروج از نشست، زیرساخت linger فعال باشد.
- دادهٔ کاربر در مسیر دائمی XDG قرار گیرد.
- هسته فقط روی loopback اجرا شود.
- بدون مدل، مسیر Database-First همچنان کار کند.
- تفاوت پاسخ مدل زبانی و پاسخ مستقیم پایگاه دانش در disclosure جعل نشود.

## 2. نسخهٔ مبنا

در شروع این پذیرش:

`HEAD = a782ceb7f126f37344c093047648d362e0a79820`

و `origin/main` نیز همان commit بود.

در همان checkout محلی:

`83 passed in 25.53s`

و این بررسی‌های syntax موفق بودند:

```bash
bash -n install.sh
bash -n stop.sh
bash -n scripts/simorgh-run.sh
```

## 3. معماری اجرای نهایی روی Linux

مسیر اجرا:

```text
systemd --user
    |
    v
simorgh.service
    |
    v
scripts/simorgh-run.sh
    |
    v
/home/mahdi/simorgh/.venv/bin/python main.py
    |
    v
127.0.0.1:8000
```

تنظیمات و دادهٔ شخصی از سورس پروژه جدا هستند:

```text
Config:
  /home/mahdi/.config/simorgh/

Runtime/Data:
  /home/mahdi/.local/share/simorgh/

Memory:
  /home/mahdi/.local/share/simorgh/memory

Models:
  /home/mahdi/.local/share/simorgh/models
```

در پذیرش واقعی این وضعیت مشاهده شد:

```text
enabled
active
Linger=yes
```

و process واقعی:

```text
/home/mahdi/simorgh/.venv/bin/python main.py
```

Health واقعی نیز برگرداند:

```json
{"status":"healthy","version":"0.1.0","python_version":"3.13.15"}
```

## 4. خطاهای پیدا شده و راه‌حل آن‌ها

### 4.1. نشت HOME تستی به shell

در یک smoke test قبلی، `HOME` به یک مسیر موقت تغییر کرده بود. بعد از پایان تست، آن متغیر در shell تعاملی باقی مانده بود و:

```text
cd ~/simorgh
bash: cd: /tmp/tmp.ASBJOMSUN1/simorgh: No such file or directory
```

این به معنای خراب بودن repository نبود؛ shell environment خراب شده بود.

راه‌حل:

```bash
export HOME=/home/mahdi
cd /home/mahdi/simorgh
```

### 4.2. برخورد سرویس قدیمی با smoke test

نسخهٔ قدیمی:

```text
simorgh-core.service
```

در سطح system systemd فعال بود و از runtime دیگری اجرا می‌شد:

```text
/home/mahdi/SimorghCore/venv/bin/python3
```

این سرویس باعث شد یک smoke test قبلی به پورت 8000 وصل شود ولی در واقع پاسخ نسخهٔ قدیمی را بگیرد. نشانه‌های قطعی:

```text
python_version = 3.10.12
/ -> 404
/api/bootstrap -> 404
/terminal/learn -> 404
```

راه‌حل اعمال‌شده:

```bash
sudo systemctl disable --now simorgh-core.service
```

و نتیجهٔ مشاهده‌شده:

```text
inactive
disabled
```

سرویس جدید بعد از آن از `.venv` خود پروژه اجرا شد.

### 4.3. مسیر XDG هنوز به /tmp اشاره می‌کرد

در اولین نصب service جدید، اگرچه `HOME` اصلاح شده بود، متغیرهای:

```text
XDG_CONFIG_HOME
XDG_DATA_HOME
```

هنوز از تست موقت قبلی اثر گرفته بودند. installer بنابراین runtime را اینجا ساخت:

```text
/tmp/tmp.ASBJOMSUN1/.local/share/simorgh
```

راه‌حل:

```bash
unset XDG_CONFIG_HOME
unset XDG_DATA_HOME
unset SIMORGH_RUNTIME_DIR
unset SIMORGH_PORT
rm -rf /home/mahdi/.config/simorgh
rm -rf /home/mahdi/.local/share/simorgh
```

و نصب مجدد با محیط تمیز انجام شد.

وضعیت نهایی مشاهده‌شده:

```text
runtime_dir = /home/mahdi/.local/share/simorgh
port = 8000
privacy_mode = local-only
```

### 4.4. PID باقی‌مانده در ریشهٔ repo

یک `simorgh.pid` متعلق به اجرای قدیمی در checkout محلی ظاهر شده بود.

برای جلوگیری از اختلاط launcher قدیمی با service جدید حذف شد:

```bash
rm -f /home/mahdi/simorgh/simorgh.pid
```

service فعلی PID خود را از systemd می‌گیرد و runner جدید فایل PID را در runtime کاربر نگه می‌دارد.

### 4.5. شکست AppImage به علت ARG_MAX

در اولین build AppImage، JSON بزرگ release Python به‌صورت environment variable عبور داده می‌شد و از محدودیت آرگومان محیط سیستم عبور کرد.

راه‌حل: JSON در فایل ذخیره شد و فقط نام فایل/version به parser داده شد.

این اصلاح در PR #27 ادغام شد.

### 4.6. شکست appimagetool در پیدا کردن desktop file

`appimagetool` فایل desktop را در محل مورد انتظار پیدا نمی‌کرد، چون فقط نسخهٔ استاندارد زیر `usr/share/applications` وجود داشت.

راه‌حل: desktop entry علاوه بر محل استاندارد، در ریشهٔ AppDir نیز قرار گرفت.

این اصلاح در PR #28 ادغام شد.

### 4.7. smoke test اشتباه روی سرویس قدیمی

Smoke test قبلی فقط «پورت 8000» را می‌دید و هویت پردازش را کنترل نمی‌کرد.

در نتیجه ممکن بود تست سبز به نظر برسد ولی پاسخ سرویس قدیمی باشد.

راه‌حل‌های اعمال‌شده:

- بررسی PID و command line برای runtime بسته‌شدهٔ AppImage.
- استفاده از پورت ثبت‌شده در `runtime.json`.
- تطبیق `python_version` با Python بسته‌شده.
- بررسی endpoint ریشه و `/api/bootstrap`.

این تفاوت مهم است: **پورت باز بودن به معنی درست بودن process نیست.**

## 5. Crash Recovery

این آزمایش روی ماشین واقعی انجام شد.

قبل از crash:

```text
STATE=active
OLD_PID=39131
```

سپس:

```bash
kill -9 39131
```

بعد از پنج ثانیه:

```text
STATE=active
NEW_PID=40377
```

و:

```json
{"status":"healthy","version":"0.1.0","python_version":"3.13.15"}
```

نتیجه: `Restart=always` در systemd user service عملاً عمل کرده است.

## 6. Linger

روی ماشین واقعی:

```text
Linger=yes
```

این تنظیم برای ادامهٔ user service بعد از خروج از نشست کاربر فعال شده است.

**[NOT VERIFIED]** هنوز logout/login یا reboot فیزیکی در این دور به‌عنوان آزمایش تخریبی کامل انجام نشده است. بنابراین این سند ادعا نمی‌کند که reboot end-to-end مشاهده شده؛ فقط فعال بودن زیرساخت linger تأیید شده است.

## 7. پایگاه داده canonical

Git LFS pointer برای:

`data/simorgh_full.db`

این digest را ثبت می‌کند:

```text
SHA-256:
09a60e42883fb65da50b0d93e1233911dba8e7a8c5a5ea1f2b664a1a8d6efc75

size:
392294400 bytes
```

installer برای LFS materialization منطق دریافت و تطبیق SHA-256 دارد.

## 8. Database-First

در UI واقعی مشاهده شد:

```text
پایگاه دانش: Database-First فعال
بدون مدل: نیاز ندارد
Offline: فعال
مدل فعال: ندارد
```

و یک پرسش بدون مدل توانست پاسخ مستقیم از پایگاه دانش محلی بازیابی کند و منبع را نشان دهد.

نمونهٔ رفتار observed:

```text
مدل زبانی محلی در دسترس نیست؛ این پاسخ مستقیماً از پایگاه دانش محلی سیمرغ ساخته شده است.
...
منبع بالا مستقیماً بازیابی شده است؛ تفسیر یا نتیجه‌گیری مدل زبانی در آن دخیل نیست.
```

این با اصول `KNOWN ≠ INFERRED` و `Provenance > elegance` سازگار است.

## 9. اصلاح نهایی disclosure

در بازبینی UI یک تناقض پیدا شد: پاسخ Database-First در کنار متن درستِ «بدون مدل» با برچسب عمومی AI نیز نمایش داده می‌شد.

ریشهٔ مسئله در این بود که endpoint `/chat` و UI برای هر پاسخ مقدار `ai_disclosure` را نمایش می‌دادند و middleware نیز مقدار `X-SIMORGH-AI-GENERATED: true` را پیش‌فرض می‌کرد.

اصلاح نهایی:

### پاسخ مدل

```text
ai_generated = true
[AI disclosure]
این پاسخ با استفاده از مدل زبانی محلی تولید شده است؛ پیش از تصمیم‌گیری، آن را بررسی کنید.
```

### پاسخ Database-First

```text
ai_generated = false
[Knowledge disclosure]
این پاسخ مستقیماً از پایگاه دانش محلی سیمرغ بازیابی شده است و در تولید آن از مدل زبانی استفاده نشده است.
```

همچنین header ماشین‌خوان:

```text
X-SIMORGH-AI-GENERATED: true
```

یا:

```text
X-SIMORGH-AI-GENERATED: false
```

و regression test جداگانه برای هر دو حالت اضافه شد.

## 10. مدل‌های محلی

روی ماشین مورد آزمایش، پروفایل سخت‌افزار به‌صورت UI گزارش شد:

```text
Linux
x86_64
4 threads
RAM ≈ 7.69 GB
GPU = GeForce GT 730
tier = small
```

کاتالوگ محلی مدل‌ها conservative است و نصب خودکار را ممنوع می‌کند.

برای مدل انتخابی، زنجیرهٔ مورد انتظار:

```text
explicit user action
  -> hardware compatibility
  -> download
  -> SHA-256 verification
  -> provenance/license check
  -> backend verification
  -> local llama.cpp
  -> loopback endpoint
```

**[NOT VERIFIED]** در این پذیرش، نصب کامل Qwen2.5 1.5B تا اولین generation به‌عنوان یک آزمون end-to-end مستقل ثبت نشده است. بنابراین نباید موفقیت آن را از روی نمایش UI نتیجه گرفت.

## 11. مرز شبکه و حریم خصوصی

رفتار فعلی پروژه:

- bind پیش‌فرض روی loopback
- non-loopback بدون `SIMORGH_KEY` باید fail closed شود
- external session به شناسهٔ opaque نیاز دارد
- شناسهٔ session قبل از ذخیرهٔ حافظه hash می‌شود
- API key پیش‌فرض اجباری نیست
- cloud account پیش‌فرض اجباری نیست
- telemetry اجباری نیست

تعهدات deployment اینترنتی مانند TLS، rate limit، allowed-origin/host و incident response همچنان مسئولیت deployment هستند.

## 12. وضعیت GitHub

PRهای مربوط به مسیر user-first و سرویس پایدار ادغام شده‌اند:

- #25: user-first runtime foundation
- #26: self-contained AppImage
- #27: اصلاح ARG_MAX در AppImage builder
- #28: اصلاح desktop discovery AppImage
- #29: persistent user service
- #30: service idempotency
- #31: final installer health-flow fix

commit مبنا:

`a782ceb7f126f37344c093047648d362e0a79820`

در زمان این گزارش، GitHub connector برای این commit workflow run ثبت‌شده‌ای برنگرداند و status check مستقیمی نیز گزارش نشد. بنابراین این سند **[NOT VERIFIED]** بودن CI برای همین commit را صریحاً نگه می‌دارد و از «CI سبز» نتیجه‌گیری نمی‌کند.

## 13. معیارهای پذیرش فعلی

| مورد | وضعیت | شاهد |
|---|---|---|
| Git local = origin/main | PASS | commit یکسان |
| 83 تست Python | PASS | اجرای واقعی محلی |
| shell syntax | PASS | سه اسکریپت |
| old service disabled | PASS | inactive/disabled |
| new user service enabled | PASS | systemd user |
| new user service active | PASS | systemd user |
| repo-local Python | PASS | process واقعی |
| Python 3.13.15 | PASS | /health |
| persistent runtime path | PASS | /home/mahdi/.local/share/simorgh |
| runtime config path | PASS | /home/mahdi/.config/simorgh |
| Linger enabled | PASS | Linger=yes |
| crash recovery | PASS | PID 39131 -> 40377 |
| health after crash | PASS | healthy |
| Database-First without model | PASS | UI/runtime evidence |
| AI/knowledge disclosure distinction | FIXED IN THIS AUDIT | code + regression test |
| logout end-to-end | [NOT VERIFIED] | هنوز عمداً انجام نشده |
| reboot end-to-end | [NOT VERIFIED] | هنوز عمداً انجام نشده |
| Qwen 1.5B full install/generation | [NOT VERIFIED] | آزمون مستقل ثبت نشده |
| current commit CI green | [NOT VERIFIED] | workflow run/status موجود نبود |
| public release/legal clearance | [NOT VERIFIED] | این گزارش clearance حقوقی ایجاد نمی‌کند |

## 14. دستور ممیزی تکرارپذیر

بعد از pull آخرین تغییرات:

```bash
cd ~/simorgh
chmod +x scripts/simorgh-final-audit.sh
./scripts/simorgh-final-audit.sh
```

برای آزمون تخریبی restart خودکار:

```bash
./scripts/simorgh-final-audit.sh --crash-test
```

آزمون دوم عمدی است: process اصلی را با `kill -9` می‌کشد و انتظار دارد systemd PID جدید بسازد و health برگردد.

## 15. جمع‌بندی پذیرش

در تاریخ 2026-09-18 روی Linux Mint مورد آزمایش، هستهٔ محلی سیمرغ با Python 3.13.15 از خود repository اجرا شد، systemd user service فعال شد، linger فعال شد، سرویس پس از `kill -9` خودکار برگشت و health دوباره سالم شد. مسیر داده از مسیر موقت به مسیر دائمی کاربر اصلاح شد و سرویس قدیمی که باعث آلودگی smoke test می‌شد خاموش شد.

این نقطه را می‌توان **پایان پذیرش مسیر Persistent Local Core روی ماشین آزمایش‌شده** دانست، با این تفاوت شفاف که logout/reboot واقعی، نصب کامل Qwen 1.5B و CI همان commit هنوز به‌عنوان مشاهدهٔ مستقیم ثبت نشده‌اند.

این تفکیک عمدی است: «کار می‌کند» فقط جایی نوشته شده که شاهد اجرایی داریم.
