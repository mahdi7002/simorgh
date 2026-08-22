from fastapi import FastAPI, HTTPException, File, UploadFile, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3, json, os, tempfile, subprocess
from core.engine import fast_router, agent_council, llm_interface, memory_graph, auth

app = FastAPI(title="Simorgh Core")
DB_PATH = os.path.join("data", "simorgh.db")

class Query(BaseModel):
    text: str

@app.get("/status")
async def status():
    return {"status": "online", "llm": True, "vosk": os.path.exists("models/vosk-model-fa")}

@app.post("/ask")
async def ask(query: Query, x_token: str = Header(None)):
    if not auth.verify_token(x_token or ""):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    resolved = fast_router.resolve(query.text)
    if resolved["cached"]:
        return {"response": resolved["response"]}
    agent_resp = agent_council.deliberate(resolved["intent"], {
        "cause": resolved.get("cause", ""),
        "emotion": resolved.get("emotion", ""),
        "understanding": resolved.get("understanding", ""),
        "description": resolved.get("understanding", "")
    })
    if agent_resp != "نیاز به LLM داریم.":
        memory_graph.save_interaction(query.text, agent_resp)
        return {"response": agent_resp}
    llm_resp = llm_interface.query_llm(query.text)
    memory_graph.save_interaction(query.text, llm_resp)
    return {"response": llm_resp}

@app.post("/voice")
async def voice(file: UploadFile = File(...), x_token: str = Header(None)):
    if not auth.verify_token(x_token or ""):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    converted = tmp_path + "_conv.wav"
    try:
        subprocess.run(["ffmpeg", "-y", "-i", tmp_path,
                        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", converted],
                       check=True, capture_output=True)
        from core.engine import stt
        text = stt.transcribe_wav(converted)
        if not text:
            text = "[صدای نامشخص]"
    except subprocess.CalledProcessError:
        text = "[خطا در تبدیل فایل صوتی]"
    except Exception as e:
        text = f"[خطا در تشخیص گفتار: {e}]"
    finally:
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        if os.path.exists(converted): os.unlink(converted)
    return await ask(Query(text=text), x_token=x_token)

@app.get("/dashboard")
async def get_dashboard():
    return FileResponse("dashboard/index.html")

@app.get("/tasks")
async def get_tasks():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return {"tasks": [{"id": r[0], "phase": r[1], "week": r[2], "title": r[3],
                       "description": r[4], "done": bool(r[5]), "tags": r[6]} for r in rows]}

@app.patch("/tasks/{task_id}")
async def toggle_task(task_id: int, x_token: str = Header(None)):
    if not auth.verify_token(x_token or ""):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    conn = sqlite3.connect(DB_PATH)
    current = conn.execute("SELECT done FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not current:
        raise HTTPException(status_code=404, detail="Task not found")
    new_val = 1 if current[0] == 0 else 0
    conn.execute("UPDATE tasks SET done=? WHERE id=?", (new_val, task_id))
    conn.commit()
    conn.close()
    return {"id": task_id, "done": bool(new_val)}

@app.post("/memory/short_term")
async def add_short_term(session_id: str, role: str, content: str, x_token: str = Header(None)):
    if not auth.verify_token(x_token or ""):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO short_term_memory (session_id, role, content) VALUES (?,?,?)",
                 (session_id, role, content))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/memory/short_term/{session_id}")
async def get_short_term(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT role, content FROM short_term_memory WHERE session_id=? ORDER BY timestamp",
                        (session_id,)).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

from core.engine import cultural_retriever, knowledge_graph
cultural_retriever.load_cultural_data()

@app.get("/cultural/search")
async def search_cultural(q: str, limit: int = 3):
    return {"query": q, "results": cultural_retriever.search_cultural(q, limit)}

@app.get("/knowledge/connections")
async def hidden_connections():
    return {"hidden_connections": knowledge_graph.find_hidden_connections()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
