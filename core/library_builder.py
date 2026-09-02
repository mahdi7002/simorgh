import json, sqlite3, time, requests
from pathlib import Path
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

CATALOG_PATH = Path.home() / "simorgh" / "catalog.json"
DB_PATH = str(Path.home() / "simorgh" / "library_catalog.db")
LLAMA_URL = "http://localhost:8080/v1/chat/completions"
MAX_CHARS_FOR_PROMPT = 3000  # فقط ابتدای سند رو برای خلاصه‌سازی می‌فرستیم

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS library (
            path TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            status TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS library_fts
        USING fts5(path, title, summary, content='')
    """)
    conn.commit()
    return conn

def already_done(conn, path: str) -> bool:
    row = conn.execute("SELECT 1 FROM library WHERE path = ? AND status='done'", (path,)).fetchone()
    return row is not None

def extract_text(path: str) -> str:
    p = Path(path)
    try:
        if p.suffix.lower() == ".pdf":
            parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages[:10]:  # فقط ۱۰ صفحه اول کافیه برای خلاصه
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        else:
            return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def summarize(text: str, filename: str) -> str:
    prompt = (
        f"این متن از فایلی به نام «{filename}» است. "
        f"در حداکثر ۳ جمله فارسی بگو: ۱) موضوع این سند چیست، "
        f"۲) به چه دردی می‌خورد، ۳) چقدر تکمیل/مهم به‌نظر می‌رسد.\n\n"
        f"متن:\n{text[:MAX_CHARS_FOR_PROMPT]}"
    )
    resp = requests.post(LLAMA_URL, json={
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "repeat_penalty": 1.3,
        "max_tokens": 200,
    }, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    docs = catalog["standalone_docs_filtered"]
    conn = init_db()

    total = len(docs)
    for i, path in enumerate(docs, 1):
        if already_done(conn, path):
            continue
        text = extract_text(path)
        if len(text.strip()) < 20:
            conn.execute(
                "INSERT OR REPLACE INTO library(path, title, summary, status) VALUES (?, ?, ?, ?)",
                (path, Path(path).name, "متن قابل استخراج نبود یا خالی است.", "done")
            )
            conn.commit()
            continue
        try:
            summary = summarize(text, Path(path).name)
            status = "done"
        except Exception as e:
            summary = f"خطا: {e}"
            status = "error"

        conn.execute(
            "INSERT OR REPLACE INTO library(path, title, summary, status) VALUES (?, ?, ?, ?)",
            (path, Path(path).name, summary, status)
        )
        conn.execute(
            "INSERT INTO library_fts(path, title, summary) VALUES (?, ?, ?)",
            (path, Path(path).name, summary)
        )
        conn.commit()
        print(f"[{i}/{total}] {path} -> {status}")

    conn.close()
    print("پایان یافت.")

if __name__ == "__main__":
    main()
