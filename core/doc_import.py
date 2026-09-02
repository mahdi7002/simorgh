import sqlite3
from pathlib import Path

try:
    import pdfplumber
    import pytesseract
    from pdf2image import convert_from_path
    _PDF_LIBS_OK = True
except ImportError:
    pdfplumber = pytesseract = convert_from_path = None
    _PDF_LIBS_OK = False

from core.paths import BOOKS_DB as DB_PATH

def _require_pdf_libs():
    if not _PDF_LIBS_OK:
        raise RuntimeError(
            "کتابخانه‌های PDF نصب نیستند — برای فعال‌سازی: "
            "pip install pdfplumber pytesseract pdf2image"
        )

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS books
        USING fts5(source, chunk, content='')
    """)
    conn.commit()
    return conn

def _extract_text_pdf(path: str) -> str:
    _require_pdf_libs()
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            text_parts.append(t)
    combined = "\n".join(text_parts).strip()
    if len(combined) > 50:
        return combined
    ocr_parts = []
    images = convert_from_path(path)
    for img in images:
        ocr_parts.append(pytesseract.image_to_string(img, lang="fas"))
    return "\n".join(ocr_parts)

def import_file(path: str) -> int:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        text = _extract_text_pdf(str(p))
    else:
        text = p.read_text(encoding="utf-8", errors="ignore")

    chunks = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]

    conn = _init_db()
    for chunk in chunks:
        conn.execute("INSERT INTO books(source, chunk) VALUES (?, ?)", (p.name, chunk))
    conn.commit()
    conn.close()
    return len(chunks)

def search_books(query: str, limit: int = 5):
    conn = _init_db()
    rows = conn.execute(
        "SELECT source, chunk FROM books WHERE books MATCH ? LIMIT ?",
        (query, limit)
    ).fetchall()
    conn.close()
    return [{"source": r[0], "chunk": r[1]} for r in rows]
