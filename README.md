# سیمرغ · Simorgh

**دستیار هوش مصنوعی آفلاین‌محور، با هویت فرهنگی فارسی و عرفانی**

ساخته‌شده با هدایت انسانی و تولید کد توسط مدل‌های هوش مصنوعی — نه ادعای رقابت با غول‌های صنعتی، بلکه چیزی که آن‌ها معمولاً نمی‌سازند: **کاملاً محلی، بدون کلید API اجباری، با پرسونا و متون فرهنگی واقعی.**

---

## استقبال

اگر تازه این مخزن را باز کرده‌اید: خوش آمدید.

سیمرغ یک محصول یک‌نفرهٔ هدایت‌شده است. نویسندۀ پروژه ([Mahdi Jafari Najafabadi](https://github.com/mahdi7002)، یزد) نیازها، معماری و پذیرش نتیجه را تعیین می‌کند؛ کد توسط مدل‌های AI نوشته و بازبینی می‌شود. هدف این نبوده که «بزرگ‌ترین مدل جهان» باشد — هدف این بوده که **روی ماشین خودتان، با احترام به محدودیت‌ها، زنده بماند و مفید باشد.**

آنچه امروز در این ریپو می‌بینید نتیجۀ مسیر شفاف است: پیدا کردن فایل خالی، حذف مسیرهای سخت‌کد، تست cold-start مثل کاربر غریبه، و اصلاح وابستگی‌ها تا `import main` بدون پشتهٔ صوت/PDF هم ممکن باشد.

> **Verification over claims.** چیزی را «کار می‌کند» نمی‌گوییم مگر اینکه واقعاً اجرا و چک شده باشد.

---

## شروع سریع (کاربر اول)

```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt

python -c "import main; print('OK', len(main.app.routes))"
python main.py
```

سپس:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/personas
curl -s -X POST http://127.0.0.1:8000/chat -d "query=سلام&agent=hakim"
```

- **بدون** سرور مدل محلی: پاسخ fallback صادقانه («مدل در دسترس نیست»).
- **با** `llama-server` (مثلاً پورت ۸۰۸۰/۸۰۸۱): چت کامل با پرسوناها.

نسخهٔ مینیمال بدون FastAPI:

```bash
python3 demo/simorgh_minimal.py --test
python3 demo/simorgh_minimal.py "عدالت چیست؟"
```

جزئیات بیشتر: [`docs/FIRST_RUN.md`](docs/FIRST_RUN.md) (اگر در شاخه باشد) و [`QUICKSTART.md`](QUICKSTART.md).

---

## چه چیزی اینجاست

| بخش | توضیح |
|-----|--------|
| `main.py` / `cli.py` | ورود سرویس و خط فرمان |
| `core/` | چت، هویت، حافظه، جستجوی قرآن/شعر، مسیرهای portable |
| `agents/` | تعاریف عامل / YAML |
| ۱۲ پرسونا | از جمله حکیم، حافظ، ناظر، رهبر، … (`GET /personas`) |
| `dashboard/` | رابط وب |
| `demo/simorgh_minimal.py` | همیشه چیزی برای اجرا دارد |
| `.github/workflows/` | نگهبانی hygiene ریپو |

**اختیاری (نصب جدا):** گفتار (`faster-whisper`)، PDF، متریک غنی‌تر (`psutil`). هستهٔ `requirements.txt` برای بالا آمدن API کافی است.

---

## اصول طراحی

1. **Offline-first** — بدون کلید API اجباری و بدون اینترنت برای هسته  
2. **Provider-agnostic** — ابر اختیاری است، پیش‌فرض خاموش  
3. **Constraint as design** — محدودیت رم/برد/Termux بخشی از معماری است، نه بهانه  
4. **Honesty** — محدودیت‌ها نوشته می‌شوند؛ ادعا بدون اجرا پذیرفته نیست  

---

## وضعیت

مخزن عمومی به‌تدریج با نسخهٔ کامل محلی هم‌تراز می‌شود (دانشنامه، شعر، قرآن، صوت). هر کامیت باید قابل‌بازبینی بماند.

برای گزارش باگ یا پیشنهاد: Issues همین ریپو.

---

## مجوز و نویسنده

- **License:** MIT — فایل [`LICENSE`](LICENSE)  
- **Author:** [Mahdi Jafari Najafabadi](https://github.com/mahdi7002) · Yazd, Iran  

همکاری با همان روحیهٔ شفافیت خوش‌آمد است — اول Issue، بعد PR کوچک و قابل‌تست.

---

## Capability Matrix

| Capability | Status | Verification |
|---|---|---|
| Offline-first core | IMPLEMENTED | CI runtime audit |
| Local LLM provider | IMPLEMENTED | Runtime-dependent |
| 12 personas | IMPLEMENTED | `/personas` + tests |
| Shared request blackboard | IMPLEMENTED | `core/orchestration/` |
| Lightweight dispatcher | IMPLEMENTED | `core/orchestration/dispatcher.py` |
| Deterministic reviewer gate | IMPLEMENTED | `core/orchestration/reviewer.py` |
| Provenance memory | IMPLEMENTED | SQLite regression tests |
| Governed self-improvement | IMPLEMENTED | policy regression tests |
| Automatic knowledge mutation | DISABLED | Human gate required |
| Full external tool-calling | EXPERIMENTAL | Persona-specific tools remain isolated |
| Semantic/LLM dispatcher | PLANNED | Lightweight rules used by default |
| Release package | PLANNED | No GitHub release yet |

### Verification policy

A capability is considered implemented only when the repository contains:
1. an executable implementation,
2. a regression test,
3. a CI path that executes the test.

Anything else is documented as experimental or planned.
