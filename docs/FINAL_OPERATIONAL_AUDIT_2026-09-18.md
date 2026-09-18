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

این نسخه از گزارش بر پایهٔ merge commit نهایی PR #41 در `main` است:

`486a255b1980095e211e863b4b1219788cd8c389`

PR #41 با squash merge ادغام شد. پیش از merge، روی همان شاخهٔ PR چهار workflow اصلی GitHub موفق شدند: CodeQL، Repo Hygiene Guard، Global Compliance Audit و Final Runtime Audit.

ممیزی واقعی ماشین پس از اصلاحات نیز:

`97 passed in 10.56s`

را گزارش کرد.

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
~/simorgh/.venv/bin/python main.py
    |
    v
127.0.0.1:8000
```

تنظیمات و دادهٔ شخصی از سورس پروژه جدا هستند:

```text
Config:
  ~/.config/simorgh/

Runtime/Data:
  ~/.local/share/simorgh/

Memory:
  ~/.local/share/simorgh/memory

Models:
  ~/.local/share/simorgh/models
```

در پذیرش واقعی این وضعیت مشاهده شد:

```text
enabled
active
Linger=yes
```

و process واقعی:

```text
~/simorgh/.venv/bin/python main.py
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
export HOME=~
cd ~/simorgh
```

### 4.2. برخورد سرویس قدیمی با smoke test

نسخهٔ قدیمی:

```text
simorgh-core.service
```

در سطح system systemd فعال بود و از runtime دیگری اجرا می‌شد:

```text
~/SimorghCore/venv/bin/python3
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
rm -rf ~/.config/simorgh
rm -rf ~/.local/share/simorgh
```

و نصب مجدد با محیط تمیز انجام شد.

وضعیت نهایی مشاهده‌شده:

```text
runtime_dir = ~/.local/share/simorgh
port = 8000
privacy_mode = local-only
```

### 4.4. PID باقی‌مانده در ریشهٔ repo

یک `simorgh.pid` متعلق به اجرای قدیمی در checkout محلی ظاهر شده بود.

برای جلوگیری از اختلاط launcher قدیمی با service جدید حذف شد:

```bash
rm -f ~/simorgh/simorgh.pid
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

### 4.8. false negative در crash-recovery audit

در اجرای واقعی ممیزی نهایی، systemd پردازش جدید را به‌درستی ساخت:

```text
OLD_PID=41958
NEW_PID=42393
```

اما audit بلافاصله پس از مشاهدهٔ PID جدید یک درخواست `curl` به `/health` فرستاد. در همان فاصلهٔ کوتاه، uvicorn هنوز در حال آماده‌شدن بود و درخواست با:

```text
curl: (7) Failed to connect to 127.0.0.1 port 8000
```

برگشت.

بنابراین نتیجهٔ نخست audit:

```text
service auto-restarted = PASS
health recovered = FAIL
```

بود، در حالی که چند لحظه بعد بررسی مستقل:

```json
{"status":"healthy","version":"0.1.0","python_version":"3.13.15"}
```

را برگرداند.

این یک **race condition در خود ابزار ممیزی** بود، نه failure سرویس.

راه‌حل در PR #34 اعمال شد: audit پس از مشاهدهٔ PID جدید، برای `/health` به‌صورت polling تا ۱۰ ثانیه صبر می‌کند. سپس PR در `main` ادغام شد.

این تجربه نیز در طراحی پذیرش ثبت شد: **PID جدید، readiness نیست؛ readiness باید با endpoint واقعی سنجیده شود.**

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

### گسترش provenance به همهٔ سطوح پاسخ

در بازبینی بعدی یک نقص باقی‌مانده در خارج از `/chat` پیدا شد: `/ask`، `/orchestrate` و `/voice` هنوز می‌توانستند پاسخ بدون مدل را با نشانهٔ عمومی AI همراه کنند. علاوه بر آن، سه agent قدیمی در نبود مدل متن ساختگیِ شبیه خروجی مدل تولید می‌کردند.

در PR #37 اصلاح شد:

- fallbackهای مصنوعی Hakim/Nazer/Rahbar حذف و به `None` تبدیل شدند تا نبود مدل جعل نشود.
- `AgentManager` در نبود مدل به fallback قطعی Database-First برمی‌گردد و metadata تولید را حفظ می‌کند.
- `Orchestrator` provenance هر agent را نگه می‌دارد و `main.py` مقدار aggregate `ai_generated` را برمی‌گرداند.
- `/ask` و `/orchestrate` همان قرارداد disclosure مدل/دانش را مانند `/chat` ارائه می‌کنند.
- `/voice` پرچم generation متن را به header منتقل می‌کند.
- UI به‌جای نمایش ثابت `[AI disclosure]`، label متناسب با provenance را نشان می‌دهد.

این تغییرات در کد و تست regression ثبت شده‌اند، اما **[NOT VERIFIED]** است که چهار تست جدید روی ماشین Linux مورد آزمایش پس از merge اجرا شده باشند؛ آخرین اجرای واقعی گزارش‌شده قبل از PR #37 همان `84 passed` بود.

## 10. مدل‌های محلی

روی ماشین مورد آزمایش:

```text
Linux
x86_64
4 CPU threads
RAM ≈ 7.69 GB
GPU = GeForce GT 730
tier = small
```

مدل انتخابی:

```text
Qwen2.5 1.5B Instruct Q4_K_M
file = qwen2.5-1.5b-instruct-q4_k_m.gguf
license = Apache-2.0
```

SHA-256 واقعی فایل مدل با مقدار pinned برابر است:

```text
6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e
```

نصب end-to-end روی همین ماشین واقعاً انجام شد:

```text
managed backend = http://127.0.0.1:8081
llama.cpp release = b11026
managed PID = 56971
loaded model = ~/.local/share/simorgh/models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

همزمان backend قدیمی و غیرمدیریت‌شده روی:

```text
127.0.0.1:8080
```

باقی ماند و SIMORGH آن را به‌جای backend خودش استفاده نکرد.

آزمون مستقیم `/v1/chat/completions` روی backend مدیریت‌شده پاسخ واقعی تولید کرد. در یکی از آزمون‌ها 35 توکن در حدود 3.14 ثانیه تولید شد.

آزمون مسیر کامل:

```text
POST /chat
agent = hakim
HTTP 200
ai_generated = true
X-SIMORGH-AI-GENERATED: true
```

زمان یک آزمون واقعی `/chat` حدود 5.9 ثانیه بود.

### محدودیت کیفیت مدل

این شواهد فقط اجرای واقعی مدل و مسیر provenance را ثابت می‌کنند، نه صحت معنایی پاسخ.

در آزمون‌های واقعی، Qwen2.5 1.5B به پرسش سادهٔ «سیمرغ چیست؟» پاسخ نادرست تولید کرد. بنابراین:

```text
Backend works           = PASS
Real model generation   = PASS
AI provenance           = PASS
Semantic answer quality = NOT PASS
```

این محدودیت به‌عنوان ضعف مدل کوچک/تنظیمات prompt ثبت می‌شود و نباید با وضعیت زیرساخت اشتباه گرفته شود.

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

PRهای مسیر user-first و سخت‌سازی عملیاتی:

- #25: user-first runtime foundation
- #26: self-contained AppImage
- #27: اصلاح ARG_MAX در AppImage builder
- #28: اصلاح desktop discovery AppImage
- #29: persistent user service
- #30: service idempotency
- #31: final installer health-flow fix
- #34: crash-recovery audit readiness polling
- #35: documentation of the crash-recovery audit race
- #36: synchronization of the final audit
- #37: unified provenance across response endpoints
- #41: repair local model bootstrap/backend selection و hardening نهایی آن

PR #41 در تاریخ 2026-09-18 با squash merge ادغام شد.

merge commit فعلی `main`:

`486a255b1980095e211e863b4b1219788cd8c389`

شواهد CI پیش از merge برای head PR #41:

```text
CodeQL                      PASS
Repo Hygiene Guard          PASS
SIMORGH Global Compliance   PASS
SIMORGH Final Runtime Audit PASS
```

این گزارش **ادعا نمی‌کند که CI همان merge commit به‌صورت مستقل بعد از merge مجدداً PASS شده است**؛ connector مورد استفاده workflowهای مرتبط با PR را برای این commit merge مستقیماً گزارش نمی‌کند.

## 13. معیارهای پذیرش فعلی

| مورد | وضعیت | شاهد |
|---|---|---|
| Git local = origin/main | PASS | commit یکسان |
| 97 تست Python | PASS | اجرای واقعی محلی روی head PR #41 پیش از merge |
| shell syntax | PASS | سه اسکریپت |
| old service disabled | PASS | inactive/disabled |
| new user service enabled | PASS | systemd user |
| new user service active | PASS | systemd user |
| repo-local Python | PASS | process واقعی |
| Python 3.13.15 | PASS | /health |
| persistent runtime path | PASS | ~/.local/share/simorgh |
| runtime config path | PASS | ~/.config/simorgh |
| Linger enabled | PASS | Linger=yes |
| crash recovery | PASS | PID 39131 -> 40377 |
| health after crash | PASS | healthy |
| Database-First without model | PASS | UI/runtime evidence |
| AI/knowledge disclosure distinction in `/chat` | PASS | code + regression test + real local audit |
| provenance consistency in `/ask`, `/orchestrate`, `/voice` | [NOT VERIFIED] | PR #37 merged؛ post-merge local execution مخصوص این سه مسیر ثبت نشده |
| logout end-to-end | [NOT VERIFIED] | هنوز عمداً انجام نشده |
| reboot end-to-end | [NOT VERIFIED] | هنوز عمداً انجام نشده |
| Qwen 1.5B full install/generation | PASS | bootstrap واقعی + `/v1/models` + generation + `/chat` |
| PR #41 CI green before merge | PASS | چهار workflow اصلی قبل از merge موفق شدند |
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

در تاریخ 2026-09-18، مسیر اصلی اجرای محلی SIMORGH روی ماشین Linux مورد آزمایش به یک وضعیت عملیاتی قابل تکرار رسید:

- checkout محلی با head شاخهٔ PR #41 دقیقاً هم‌تراز GitHub شد؛
- 97 تست محلی PASS شد؛
- PR #41 پس از سبز شدن چهار workflow اصلی با squash merge وارد `main` شد؛
- Qwen2.5 1.5B با SHA-256 pinned واقعاً نصب و اجرا شد؛
- backend مدیریت‌شدهٔ SIMORGH روی `127.0.0.1:8081` راه افتاد؛
- backend غیرمدیریت‌شدهٔ موجود روی `127.0.0.1:8080` دست‌نخورده باقی ماند؛
- مسیر کامل `/chat` واقعاً از مدل استفاده کرد و provenance صحیح را اعلام کرد؛
- تنظیمات fast/quality backend در runtime کاربر persist شدند؛
- process و model identity در lifecycle backend سخت‌گیرانه‌تر بررسی می‌شوند.

محدودیت باقی‌ماندهٔ مهم این است که مدل Qwen2.5 1.5B روی همین پرسش‌های پایه هنوز پاسخ معنایی قابل‌اعتمادی تولید نمی‌کند. بنابراین release این نسخه باید **پایداری زیرساخت، provenance و قابلیت اجرای مدل** را ادعا کند، نه دقت عمومی مدل را.

همچنین logout/reboot فیزیکی end-to-end و اجرای post-merge مستقلِ همهٔ endpointهای provenance هنوز به‌طور مستقیم مشاهده و ثبت نشده‌اند.

این تفکیک عمدی است:

```text
Installed       ≠ Accurate
Generated       ≠ Verified
Healthy         ≠ Correct
```
