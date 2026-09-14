# راهنمای سریع سیمرغ

این مسیر برای اولین اجرای یک کاربر تازه‌وارد نوشته شده است. هدف: **کمترین اصطکاک، بدون ادعای پنهان.**

## پیش‌نیازها

- Python 3.10+
- pip
- ffmpeg فقط برای workflowهای صوتی/تبدیل فایل
- برای هستهٔ Python، سیستم معمولی با حدود 8GB RAM کافی است؛ اجرای مدل محلی به حافظه و اندازهٔ مدل وابسته است.

## 1. دریافت و نصب هسته

```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## 2. اولین بررسی، بدون مدل محلی

```bash
python -c "import main; print('OK', len(main.app.routes))"
python demo/simorgh_minimal.py --test
```

اگر خروجی `TEST PASS` دیدید، مسیر مینیمال اجرا شده است. نبودن مدل محلی نباید به‌عنوان «مدل هوش مصنوعی فعال است» گزارش شود.

## 3. اجرای سرویس

```bash
python main.py
```

در یک ترمینال دیگر:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/personas
curl -s -X POST http://127.0.0.1:8000/chat -d "query=سلام&agent=hakim"
```

داشبورد، در صورت فعال بودن مسیر آن:

```text
http://127.0.0.1:8000/dashboard/
```

## 4. اجرای مدل زبانی محلی

سیمرغ می‌تواند به endpoint سازگار با OpenAI روی loopback متصل شود. تنظیم پیش‌فرض پروژه از `127.0.0.1:8080` استفاده می‌کند و مسیر کیفیت نیز می‌تواند روی `127.0.0.1:8081` باشد.

نمونهٔ متغیر محیطی:

```bash
export SIMORGH_LLM_URL=http://127.0.0.1:8080/v1/chat/completions
python demo/simorgh_minimal.py "عدالت چیست؟"
```

هیچ API key یا حساب ابری برای هسته اجباری نیست.

## 5. وابستگی‌های اختیاری

برای PDF / OCR / گفتار:

```bash
python -m pip install -r requirements-optional.txt
```

برای STT محلی، مدل و پیاده‌سازی را متناسب با سخت‌افزار خود انتخاب کنید. نبود این وابستگی‌ها نباید مانع بالا آمدن هسته شود.

## 6. تست کامل

```bash
python -m pip install pytest httpx
python -m pytest -q
python demo/simorgh_minimal.py --test
python persona_chat.py --test
```

نکته: نام بستهٔ تست HTTP، `httpx` است، نه `httpx2`.

## 7. مسیرهای قابل تنظیم

مسیرهای داده، حافظه، dashboard، Piper و سایر فایل‌های runtime از طریق متغیرهای `SIMORGH_*` قابل override هستند. هسته نباید برای اجرا به مسیرهایی مانند `/home/<user>` وابسته باشد.

## 8. کنترل خودبهبود

قوانین خودبهبود در `governance/constitution.yaml` و `core/self_improvement_policy.py` تعریف شده‌اند.

اصل عملی:

- تغییرهای اطلاعاتی و برگشت‌پذیر می‌توانند در محدودهٔ سیاست خودکار باشند.
- تغییر اجرایی فقط در sandbox و پس از ارزیابی مجاز است.
- افزایش دسترسی، شبکه، تغییر evaluator و تغییر قانون اساسی به تأیید انسان نیاز دارند.

**Proposal ≠ Command.** پیشنهاد سیستم، مجوز اجرا نیست.

## اگر چیزی کار نکرد

اول خطا را بدون حذف traceback ثبت کنید. سپس این موارد را گزارش کنید:

1. سیستم‌عامل و نسخهٔ Python
2. دستور دقیق اجراشده
3. خروجی کامل خطا
4. اینکه مدل محلی فعال بوده یا نه
5. نتیجهٔ `python -m pytest -q`

Issue کوچک و قابل‌بازآزمایی، از گزارش کلی مثل «کار نمی‌کند» بسیار مفیدتر است.
