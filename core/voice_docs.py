from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil, tempfile
from pathlib import Path

try:
    from core.tts import synthesize
except Exception:
    synthesize = None
try:
    from core.stt import transcribe
except Exception:
    transcribe = None
try:
    from core.doc_import import import_file, search_books
except Exception:
    def import_file(*a, **k):
        raise RuntimeError('doc_import unavailable')
    def search_books(*a, **k):
        return []

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak")
def speak(req: SpeakRequest):
    if synthesize is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail='TTS unavailable')
    path = synthesize(req.text)
    return FileResponse(path, media_type="audio/wav")

@router.post("/listen")
async def listen(file: UploadFile = File(...)):
    if transcribe is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail='STT unavailable')
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    text = transcribe(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)
    return {"text": text}

@router.post("/import")
async def import_doc(file: UploadFile = File(...)):
    dest = Path.home() / "simorgh" / "imports" / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    count = import_file(str(dest))
    return {"file": file.filename, "chunks_indexed": count}

@router.get("/books-search")
def books_search(q: str):
    return search_books(q)

from core.yazd_lore import tell_story_about, format_for_prompt as format_yazd_lore
from core.memory_journal import add_entry, get_entries, search_entries

class JournalEntry(BaseModel):
    place: str
    note: str

@router.post("/journal")
def journal_add(entry: JournalEntry):
    entry_id = add_entry(entry.place, entry.note)
    return {"id": entry_id, "status": "ثبت شد"}

@router.get("/journal")
def journal_list(limit: int = 20):
    return get_entries(limit)

@router.get("/journal-search")
def journal_search(q: str):
    return search_entries(q)

@router.get("/yazd-story")
def yazd_story(place: str):
    story = tell_story_about(place)
    return {"place": place, "story": story or "روایتی برای این مکان هنوز ثبت نشده."}
