# GitHub Release — v1.0.0 (پیش‌نویس متن انتشار)

**عنوان پیشنهادی:** `v1.0.0 — اولین نقطهٔ قابل‌اجرای عمومی سیمرغ`

## فارسی

این اولین برچسب رسمی است که می‌گوید: **کلون کن، نصب هسته کن، سرور را بالا بیاور.**

سیمرغ یک دستیار آفلاین‌محور با هویت فارسی/عرفانی است. ۱۲ پرسونا، مسیر portable، و وابستگی‌های اختیاری برای صوت و PDF.

آنچه در این نسخه عمداً نیست: ادعای برابری با مدل‌های عظیم ابری. آنچه هست: شفافیت مسیر، تست cold-start، و احترام به محدودیت سخت‌افزار کاربر.

### شروع

```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh && pip install -r requirements.txt
python -c "import main; print('OK')"
python main.py
```

### تغییرات مهم نسبت به وضعیت آشفتهٔ میانی

- بازیابی و پایدارسازی ماژول‌های core  
- حذف وابستگی اجباری به پشته‌های سنگین برای boot  
- مستند اولین اجرا  

---

## English

**Simorgh v1.0.0** — first public “clone and run the core” marker.

Offline-first Persian cultural assistant direction. Twelve personas. Optional speech/PDF stacks. Honest fallback when no local LLM is running.

Not a claim to out-scale frontier labs. A claim to be **runnable, reviewable, and culturally specific.**

See README and `docs/FIRST_RUN.md`.
