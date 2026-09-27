import os, re
from fastapi import FastAPI, Form
import uvicorn

ROOT = "/home/mahdi/SimorghCore/personas"

def find_text_dir(name):
    # حذف فاصله، زیرخط و نیم‌فاصله برای تطبیق
    key = name.replace(' ', '').replace('_', '').replace('\u200c', '')
    for folder in os.listdir(ROOT):
        folder_path = os.path.join(ROOT, folder)
        if not os.path.isdir(folder_path):
            continue
        cmp = folder.replace(' ', '').replace('_', '').replace('\u200c', '')
        if cmp == key:
            d = os.path.join(folder_path, "text")
            if os.path.exists(d):
                return d
    return None

def load_texts(name):
    d = find_text_dir(name)
    if not d:
        return ""
    text = ""
    for f in sorted(os.listdir(d)):
        if f.endswith(".txt"):
            with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                text += fh.read() + "\n"
    return text

def search(text, question, n=800):
    words = question.split()
    sentences = re.split(r'[.؟!\n]', text)
    scored = [(sum(1 for w in words if w in s), s) for s in sentences if len(s.strip()) >= 10]
    scored.sort(key=lambda x: x[0], reverse=True)
    out, total = [], 0
    for _, s in scored:
        if total + len(s) > n: break
        out.append(s); total += len(s)
    return "\n".join(out) if out else text[:n]

app = FastAPI()
@app.post("/persona/ask")
async def ask(channel_name: str = Form(...), question: str = Form(...)):
    text = load_texts(channel_name)
    if not text: return {"response": f"داده‌ای برای {channel_name} پیدا نشد"}
    return {"channel": channel_name, "response": search(text, question)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
