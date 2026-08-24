# -*- coding: utf-8 -*-
"""
core/pdf_ingestor.py
همه‌ی فایل‌های PDF روی سیستم رو پیدا می‌کنه، متنشون رو استخراج (با pdftotext)،
دسته‌بندی، و توی simorgh.db ذخیره می‌کنه (هم متن کامل، هم تکه‌های قابل جستجو).
اجرای دوباره‌ش امنه: فقط فایل‌های جدید رو پردازش می‌کنه.
"""

import os
import re
import sqlite3
import subprocess

DB_PATH = "/home/mahdi/SimorghCore/data/simorgh.db"
SCAN_ROOTS = ["/home/mahdi"]
EXCLUDE_DIRS = {"venv", "node_modules", ".git", "__pycache__", ".cache"}
CHUNK_SIZE = 1000

CATEGORY_KEYWORDS = {
    "دینی/معنوی": ["قرآن", "تفسیر", "دین", "معنوی", "عرفان", "دعا", "صحیفه", "نهج"],
    "تاریخی": ["تاریخ", "تاریخی", "شاهنامه", "باستان"],
    "فنی/برنامه‌نویسی": ["python", "code", "software", "programming", "manual", "راهنما"],
    "ادبیات": ["دیوان", "شعر", "غزل", "مثنوی", "بوستان", "گلستان"],
}


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # ستون‌های جدید رو فقط اگه نبودن اضافه کن
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
    if "path" not in existing_cols:
        conn.execute("ALTER TABLE documents ADD COLUMN path TEXT")
    if "category" not in existing_cols:
        conn.execute("ALTER TABLE documents ADD COLUMN category TEXT")

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS book_chunks_fts
        USING fts5(doc_name, category, chunk_text)
    """)
    conn.commit()
    conn.close()


def find_pdfs():
    found = []
    for root_dir in SCAN_ROOTS:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    found.append(os.path.join(root, fn))
    return found


def extract_text(pdf_path):
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, timeout=60
        )
        return result.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️ خطا در استخراج {pdf_path}: {e}")
        return ""


def categorize(name, text_sample):
    combined = (name + " " + text_sample[:500]).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined:
                return category
    return "عمومی"


def chunk_text(text, size=CHUNK_SIZE):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return [text[i:i + size] for i in range(0, len(text), size) if text[i:i + size].strip()]


def ingest_all():
    ensure_schema()
    pdfs = find_pdfs()
    print(f"🔎 {len(pdfs)} فایل PDF پیدا شد.")

    conn = sqlite3.connect(DB_PATH)
    processed_paths = {row[0] for row in conn.execute("SELECT path FROM documents WHERE path IS NOT NULL")}

    new_count = 0
    for pdf_path in pdfs:
        if pdf_path in processed_paths:
            continue

        name = os.path.basename(pdf_path)
        text = extract_text(pdf_path)
        if not text.strip():
            print(f"⏭  متن استخراج نشد (شاید اسکن‌شده باشه): {name}")
            continue

        category = categorize(name, text)

        try:
            conn.execute(
                "INSERT OR REPLACE INTO documents (name, content, path, category) VALUES (?, ?, ?, ?)",
                (name, text, pdf_path, category),
            )
            # تکه‌های قدیمی همین فایل رو پاک کن (برای جلوگیری از تکرار در re-run)
            conn.execute("DELETE FROM book_chunks_fts WHERE doc_name = ?", (name,))
            for chunk in chunk_text(text):
                conn.execute(
                    "INSERT INTO book_chunks_fts (doc_name, category, chunk_text) VALUES (?, ?, ?)",
                    (name, category, chunk),
                )
            conn.commit()
            new_count += 1
            print(f"✅ {name}  →  دسته: {category}  ({len(text)} کاراکتر)")
        except Exception as e:
            print(f"⚠️ خطا در ذخیره {name}: {e}")

    conn.close()
    print(f"\n📊 {new_count} کتاب جدید اضافه شد.")


if __name__ == "__main__":
    ingest_all()
