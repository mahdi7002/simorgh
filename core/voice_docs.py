from pathlib import Path
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from core.paths import IMPORTS_DIR
from core.tts import synthesize
from core.stt import transcribe
from core.memory_journal import add_entry, get_entries, search_entries
from core.yazd_lore import tell_story_about

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak")
def speak(req: SpeakRequest):
    return FileResponse(synthesize(req.text), media_type="audio/wav")

@router.post("/listen")
async def listen(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        return {"text": transcribe(tmp_path)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)

@router.post("/import")
async def import_doc(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if not filename or filename in {".", ".."}:
        raise HTTPException(400, "Invalid filename")
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMPORTS_DIR / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        from core.doc_import import import_file
        count = import_file(str(dest))
        return {"file": filename, "chunks_indexed": count}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@router.get("/books-search")
def books_search(q: str):
    from core.doc_import import search_books
    return search_books(q)

class JournalEntry(BaseModel):
    place: str
    note: str

@router.post("/journal")
def journal_add(entry: JournalEntry):
    return {"id": add_entry(entry.place, entry.note), "status": "ثبت شد"}

@router.get("/journal")
def journal_list(limit: int = 20):
    return get_entries(limit)

@router.get("/journal-search")
def journal_search(q: str):
    return search_entries(q)

@router.get("/yazd-story")
def yazd_story(place: str):
    return {"place": place, "story": tell_story_about(place) or "روایتی برای این مکان هنوز ثبت نشده."}
