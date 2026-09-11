# راهنمای سریع سیمرغ

## پیش‌نیازها
- Python 3.10+
- pip
- ffmpeg فقط برای workflowهای صوتی/تبدیل فایل
- 8GB RAM برای اجرای هسته کافی است؛ مدل محلی بسته به اندازهٔ مدل حافظهٔ بیشتری می‌خواهد.

## نصب هسته
```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

## قابلیت‌های اختیاری PDF / OCR / گفتار
```bash
python -m pip install -r requirements-optional.txt
```
برای STT محلی، مدل/پیاده‌سازی انتخابی را متناسب با سخت‌افزار نصب کنید. نبود این وابستگی‌ها نباید مانع بالا آمدن هسته شود.

## اجرای هسته
```bash
python main.py
```
داشبورد:
`http://127.0.0.1:8000/dashboard/`

health check:
```bash
curl http://127.0.0.1:8000/health
```

## مدل زبانی محلی
سیمرغ به‌صورت پیش‌فرض به endpoint سازگار با OpenAI روی `127.0.0.1:8080` و در حالت کیفیت روی `127.0.0.1:8081` متصل می‌شود. آدرس را می‌توان با متغیر `SIMORGH_LLM_URL` برای اجزای سازگار با آن تغییر داد.

## مسیرهای قابل تنظیم
مسیرهای داده، حافظه، dashboard، Piper و سایر فایل‌های runtime از طریق متغیرهای `SIMORGH_*` قابل override هستند. دیگر هیچ مسیر `/home/<user>` یا dashboard مخصوص ماشین توسعه‌دهنده نباید برای اجرای هسته لازم باشد.

## تست
```bash
python -m pip install pytest
python -m pytest -q
python demo/simorgh_minimal.py --test
python persona_chat.py --test
```

## کنترل خودبهبود
قوانین خودبهبود در `governance/constitution.yaml` و `core/self_improvement_policy.py` تعریف شده‌اند:
- تغییرهای صرفاً اطلاعاتی/برگشت‌پذیر می‌توانند خودکار باشند.
- تغییر اجرایی فقط در sandbox و پس از ارزیابی مجاز است.
- افزایش دسترسی، شبکه، تغییر evaluator و تغییر قانون اساسی همیشه به تأیید انسان نیاز دارند.
