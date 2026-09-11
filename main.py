from pathlib import Path
import logging
import os
import subprocess
import uvicorn
import psutil
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from core.paths import DASHBOARD_HTML, LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "simorgh.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SIMORGH", version=os.getenv("SIMORGH_VERSION", "3.1.0"))
from core.voice_docs import router as voice_docs_router
from core.dashboard_api import router as dashboard_api_router
from core.voice_endpoint import router as voice_endpoint_router
app.include_router(voice_docs_router)
app.include_router(dashboard_api_router)
app.include_router(voice_endpoint_router)

origins = [o.strip() for o in os.getenv("SIMORGH_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["*"])

from core.understanding import UnderstandingEngine
from core.memory import MemoryEngine
from core.why_engine import WhyEngine
from agents.agent_manager import AgentManager
from core.chat import ask as chat_ask

understanding = UnderstandingEngine()
memory = MemoryEngine()
why_engine = WhyEngine()
agent_manager = AgentManager()

@app.post("/ask")
async def ask(query: str = Form(...)):
    try:
        intent = understanding.detect_intent(query)
        goal, obstacle = understanding.extract_goal_obstacle(query)
        cause = why_engine.find_cause(obstacle) if obstacle else None
        response = agent_manager.consult(goal, obstacle, cause, query)
        memory.store_conversation("default", query, response, {"intent": intent, "goal": goal, "obstacle": obstacle, "cause": cause})
        return {"response": response, "goal": goal, "obstacle": obstacle, "cause": cause, "intent": intent}
    except Exception as exc:
        logger.exception("ask failed")
        raise HTTPException(500, "Request processing failed") from exc

@app.post("/chat")
async def chat(query: str = Form(...), agent: str = Form("hakim")):
    try:
        response = chat_ask(query, agent=agent)
        memory.store_conversation("default", query, response, {"agent": agent})
        return {"response": response, "agent": agent}
    except Exception as exc:
        logger.exception("chat failed")
        raise HTTPException(500, "Chat processing failed") from exc

@app.get("/quran-search")
async def quran_search_route(q: str):
    from core.quran_search import get_quran_wisdom
    try:
        return {"results": get_quran_wisdom(q, limit=5)}
    except Exception as exc:
        logger.exception("quran search failed")
        raise HTTPException(500, "Quran search failed") from exc

@app.get("/personas")
async def personas_route():
    from core.chat import PERSONAS
    return {"personas": [{"id": k, **v} for k, v in PERSONAS.items()]}

@app.get("/dashboard/")
async def dashboard():
    if not DASHBOARD_HTML.is_file():
        raise HTTPException(404, "Dashboard not found")
    return FileResponse(DASHBOARD_HTML)

@app.get("/status")
async def status():
    services = []
    for name, port in [("simorgh-core", 8000), ("simorgh-persona", 8001), ("llama-server", 8080)]:
        try:
            r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=2)
            up = r.stdout.strip() == "active"
        except Exception:
            up = False
        services.append({"name": name, "port": port, "up": up})
    return {"cpu": psutil.cpu_percent(interval=0.1), "ram": psutil.virtual_memory().percent, "disk": psutil.disk_usage("/").percent, "services": services}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": app.version, "python_version": os.sys.version.split()[0]}

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("SIMORGH_HOST", "127.0.0.1"), port=int(os.getenv("SIMORGH_PORT", "8000")), log_level="info")
