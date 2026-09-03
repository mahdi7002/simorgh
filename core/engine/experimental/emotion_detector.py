import re

EMOTIONS = {
    "درک_و_فهم": [r"\bچرا\b", r"\bچطور\b", r"\bچگونه\b", r"\bتوضیح\b", r"\bبفهمم\b"],
    "تصمیم‌گیری": [r"\bکمک\b.*\bکن\b", r"\bپیشنهاد\b", r"\bراهنمایی\b", r"\bانتخاب\b"],
    "دیده_شدن": [r"\bخسته\b", r"\bغمگین\b", r"\bناراحت\b", r"\bفقط\s+گوش\s+کن\b", r"\bحرف\s+بزن\b"]
}

def detect_emotion(text: str) -> str:
    for emotion, patterns in EMOTIONS.items():
        for p in patterns:
            if re.search(p, text):
                return emotion
    return "درک_و_فهم"
