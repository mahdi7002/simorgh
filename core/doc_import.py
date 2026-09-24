# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
try:
    import pytesseract
except ImportError:
    pytesseract = None
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None
try:
    from core.paths import BOOKS_DB
    DB_PATH = str(BOOKS_DB)
except Exception:
    DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "books.db")

def _init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS books USING fts5(source, chunk, content='')")
    conn.commit()
    return conn

def _extract_text_pdf(path: str) -> str:
    if pdfplumber is None:
        raise RuntimeError("pip install pdfplumber")
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    combined = "\n".join(parts).strip()
    if len(combined) > 50 or convert_from_path is None or pytesseract is None:
        return combined
    return "\n".join(pytesseract.image_to_string(img, lang="fas") for img in convert_from_path(path))

def import_file(path: str) -> int:
    p = Path(path)
    text = _extract_text_pdf(str(p)) if p.suffix.lower() == ".pdf" else p.read_text(encoding="utf-8", errors="ignore")
    chunks = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]
    conn = _init_db()
    for c in chunks:
        conn.execute("INSERT INTO books(source, chunk) VALUES (?, ?)", (p.name, c))
    conn.commit(); conn.close()
    return len(chunks)

def search_books(query: str, limit: int = 5):
    conn = _init_db()
    try:
        rows = conn.execute("SELECT source, chunk FROM books WHERE books MATCH ? LIMIT ?", (query, limit)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return [{"source": r[0], "chunk": r[1]} for r in rows]
