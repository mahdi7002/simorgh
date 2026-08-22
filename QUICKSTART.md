# راهنمای سریع سیمرغ

## پیش‌نیازها
- Python 3.10+
- pip
- ffmpeg
- 8GB RAM

## نصب
```bash
git clone https://github.com/mahdi7002/simorgh.git
cd simorgh
pip install -r requirements.txt
python -c "from core.engine.memory_graph import init_db; init_db()"
```

## دانلود مدل Vosk (تشخیص گفتار فارسی)
```bash
mkdir -p models && cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip
unzip vosk-model-small-fa-0.5.zip
mv vosk-model-small-fa-0.5 vosk-model-fa
cd ..
```

## اجرا
```bash
python main.py
```
سپس مرورگر: http://localhost:8000/dashboard

## سرویس دائمی
```bash
sudo cp simorgh-core.service /etc/systemd/system/
sudo systemctl enable --now simorgh-core
```
