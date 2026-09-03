import subprocess, os

PHONE_IP = "192.168.1.4"
PHONE_PORT = "8022"
SSH_KEY = os.path.expanduser("~/.ssh/id_rsa_mesh")

def phone_available():
    """بررسی می‌کند که آیا گوشی از طریق ssh قابل دسترسی است"""
    try:
        subprocess.run(
            ["ssh", "-i", SSH_KEY, "-p", PHONE_PORT, f"termux@{PHONE_IP}", "echo online"],
            capture_output=True, timeout=5, check=True
        )
        return True
    except Exception:
        return False

def remote_ask(text):
    """ارسال پرسش به گوشی و دریافت پاسخ (در صورت در دسترس بودن)"""
    if not phone_available():
        return None
    try:
        result = subprocess.run(
            ["ssh", "-i", SSH_KEY, "-p", PHONE_PORT, f"termux@{PHONE_IP}",
             f"curl -s -X POST http://192.168.1.100:8000/ask -H 'Content-Type: application/json' -d '{{\"text\":\"{text}\"}}'"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return None
    return None
