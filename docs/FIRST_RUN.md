# اولین اجرا — شفاف برای هر کاربر

## حداقل مسیر

```bash
git clone https://github.com/mahdi7002/simorgh.git && cd simorgh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -c "import main; print('OK', len(main.app.routes))"
python main.py
```

انتظار از `import main`: چاپ `OK` و تعداد route بدون نصب `faster-whisper`.

## API

| مسیر | معنی |
|------|------|
| `GET /health` | سلامت سرویس |
| `GET /status` | وضعیت (متریک کامل با `psutil` اختیاری) |
| `GET /personas` | فهرست پرسوناها |
| `POST /chat` | `query` + اختیاری `agent` |

بدون llama-server پاسخ fallback برمی‌گردد — این رفتار عمدی است.

## اختیاری

```bash
pip install psutil                 # متریک
pip install faster-whisper         # STT
pip install pdfplumber             # PDF
```

## Termux

هسته را نصب کنید؛ از اجبار `psutil` خودداری کنید. مسیر پایدارتر برای توسعه: لینوکس دسکتاپ.
