from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os
import subprocess
try:
    import psutil
except ImportError:
    psutil = None
from pathlib import Path

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/simorgh.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simorgh", version="3.0.0")

def _safe_include(import_path: str, attr: str = "router"):
    try:
        mod = __import__(import_path, fromlist=[attr])
        app.include_router(getattr(mod, attr))
        logger.info("router loaded: %s", import_path)
    except Exception as e:
        logger.warning("router skipped %s: %s", import_path, e)

_safe_include("core.voice_docs")
_safe_include("core.dashboard_api")
_safe_include("core.voice_endpoint")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import modules
from core.understanding import UnderstandingEngine
from core.memory import MemoryEngine
from core.why_engine import WhyEngine
from agents.agent_manager import AgentManager
from core.chat import ask as chat_ask

# Initialize engines
understanding = UnderstandingEngine()
memory = MemoryEngine()
why_engine = WhyEngine()
agent_manager = AgentManager()

@app.post("/ask")
async def ask(query: str = Form(...)):
    try:
        logger.info(f"Processing query: {query}")
        intent = understanding.detect_intent(query)
        logger.info(f"Intent: {intent}")

        goal, obstacle = understanding.extract_goal_obstacle(query)
        logger.info(f"Goal: {goal}, Obstacle: {obstacle}")

        cause = why_engine.find_cause(obstacle) if obstacle else None
        logger.info(f"Cause: {cause}")

        response = agent_manager.consult(goal, obstacle, cause, query)
        logger.info(f"Response: {response}")

        return {
            "response": response,
            "goal": goal,
            "obstacle": obstacle,
            "cause": cause,
            "intent": intent
        }
    except Exception as e:
        logger.error(f"Error in /ask: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(query: str = Form(...), agent: str = Form(None), persona: str = Form(None)):
    # هم «agent» هم «persona» پذیرفته می‌شود — چون /personas از واژه‌ی
    # persona استفاده می‌کند ولی این endpoint قبلاً فقط agent می‌خواست؛
    # این‌طور هیچ‌کدام از دو نام‌گذاری کاربر را غافلگیر نمی‌کند.
    chosen_agent = agent or persona or "hakim"
    try:
        logger.info(f"Chat query: {query} (agent={chosen_agent})")
        response = chat_ask(query, agent=chosen_agent)
        return {"response": response, "agent": chosen_agent}
    except Exception as e:
        logger.error(f"Error in /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quran-search")
async def quran_search_route(q: str):
    from core.quran_search import get_quran_wisdom
    try:
        return {"results": get_quran_wisdom(q, limit=5)}
    except Exception as e:
        logger.error(f"Error in /quran-search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/personas")
async def personas_route():
    from core.chat import PERSONAS
    return {"personas": [{"id": k, **v} for k, v in PERSONAS.items()]}


@app.get("/dashboard/")
async def dashboard():
    from core.paths import DASHBOARD_HTML
    return FileResponse(str(DASHBOARD_HTML))


@app.get("/status")
async def status():
    import socket

    def port_is_open(port: str | int, timeout: float = 0.5) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
                return True
        except OSError:
            return False

    services = []
    for name, port in [("simorgh-core", 8000), ("simorgh-persona", 8001), ("llama-server", 8080)]:
        # این سرویس (simorgh-core) خودش دارد به این درخواست جواب می‌دهد —
        # پس همیشه up است، صرف‌نظر از اینکه از طریق systemd اجرا شده باشد
        # یا مستقیم با «python3 main.py». برای بقیه، اتصال واقعی به پورت
        # را چک می‌کنیم، نه وضعیت systemd (که روی کلون تازه اصلاً ثبت نشده).
        up = True if name == "simorgh-core" else port_is_open(port)
        services.append({"name": name, "port": port, "up": up})
    return {
        "cpu": (psutil.cpu_percent(interval=0.3) if psutil else None),
        "ram": (psutil.virtual_memory().percent if psutil else None),
        "disk": (psutil.disk_usage("/").percent if psutil else None),
        "services": services,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "python_version": __import__("sys").version.split()[0]
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
