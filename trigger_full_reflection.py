#!/usr/bin/env python3
import time
# صبر می‌کنیم تا سرویس اصلی کاملاً بالا بیاید
time.sleep(5)
from core.engine.reflection import run_full_reflection
run_full_reflection()
