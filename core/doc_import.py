import sqlite3
from pathlib import Path

from core.paths import BOOKS_DB


def _pdf_text(path: str) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("PDF support is not installed. Install requirements-optional.txt") from exc
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages).strip()


def _ocr_text(path: str) -> str:
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise RuntimeError("PDF OCR support is not installed. Install requirements-optional.txt") from exc
    return "\n".join(pytesseract.image_to_string(img, lang="fas") for img in convert_from_path(path)).strip()


def extract_text(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() != ".pdf":
        return p.read_text(encoding="utf-8", errors="ignore")
    text = _pdf_text(str(p))
    if len(text) > 50:
        return text
    return _ocr_text(str(p))


def _init_db() -> sqlite3.Connection:
    BOOKS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BOOKS_DB)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS books USING fts5(source, chunk)")
    conn.commit()
    return conn


def import_file(path: str) -> int:
    text = extract_text(path)
    chunks = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]
    conn = _init_db()
    source = Path(path).name
    for chunk in chunks:
        conn.execute("INSERT INTO books(source, chunk) VALUES (?, ?)", (source, chunk))
    conn.commit()
    conn.close()
    return len(chunks)


def search_books(query: str, limit: int = 5):
    conn = _init_db()
    rows = conn.execute("SELECT source, chunk FROM books WHERE books MATCH ? LIMIT ?", (query, limit)).fetchall()
    conn.close()
    return [{"source": r[0], "chunk": r[1]} for r in rows]
