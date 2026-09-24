from pathlib import Path
import hashlib
import logging
import os
import secrets
import subprocess

import psutil
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from core.body_limit import RequestBodyLimitMiddleware

from core.paths import DASHBOARD_HTML, LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_LOGGER_NAME = "simorgh"


def _configure_logging():
    """Configure SIMORGH logging once without mutating the root logger."""
    app_logger = logging.getLogger(_LOGGER_NAME)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT)
    has_file = False
    has_stream = False

    for handler in list(app_logger.handlers):
        if isinstance(handler, logging.FileHandler):
            has_file = True
            handler.setFormatter(formatter)
        elif isinstance(handler, logging.StreamHandler):
            has_stream = True
            handler.setFormatter(formatter)

    if not has_file:
        file_handler = logging.FileHandler(LOG_DIR / "simorgh.log")
        file_handler.setFormatter(formatter)
        app_logger.addHandler(file_handler)

    if not has_stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        app_logger.addHandler(stream_handler)

    return app_logger


logger = _configure_logging()

HOST = os.getenv("SIMORGH_HOST", "127.0.0.1")
PORT = int(os.getenv("SIMORGH_PORT", "8000"))
SIMORGH_KEY = os.getenv("SIMORGH_KEY")
MAX_REQUEST_BYTES = int(os.getenv("SIMORGH_MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))

if MAX_REQUEST_BYTES < 1:
    raise RuntimeError("SIMORGH_MAX_REQUEST_BYTES must be a positive integer")

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
EXTERNAL_BIND = HOST not in LOOPBACK_HOSTS
if EXTERNAL_BIND and not SIMORGH_KEY:
    raise RuntimeError(
        "Refusing non-loopback bind without explicit SIMORGH_KEY. "
        "Use 127.0.0.1/localhost for local-only mode or configure authentication."
    )

AI_DISCLOSURE = "این پاسخ با استفاده از مدل زبانی محلی تولید شده است؛ پیش از تصمیم‌گیری، آن را بررسی کنید."
KNOWLEDGE_DISCLOSURE = "این پاسخ مستقیماً از پایگاه دانش محلی سیمرغ بازیابی شده است و در تولید آن از مدل زبانی استفاده نشده است."
MAX_SESSION_HEADER = 128


def _session_id(request: Request) -> str:
    """Return a stable, non-reversible session identifier for local memory storage."""
    raw = request.headers.get("x-simorgh-session", "").strip()
    if EXTERNAL_BIND and not raw:
        raise HTTPException(400, "X-SIMORGH-SESSION is required for external sessions")
    if len(raw) > MAX_SESSION_HEADER:
        raise HTTPException(400, "X-SIMORGH-SESSION is too long")
    raw = raw or "local"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


app = FastAPI(title="SIMORGH", version=os.getenv("SIMORGH_VERSION", "0.1.0"))
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_REQUEST_BYTES)
from core.voice_docs import router as voice_docs_router
from core.dashboard_api import router as dashboard_api_router
from core.voice_endpoint import router as voice_endpoint_router
from core.bootstrap_api import router as bootstrap_api_router
app.include_router(voice_docs_router)
app.include_router(dashboard_api_router)
app.include_router(voice_endpoint_router)
app.include_router(bootstrap_api_router)

if EXTERNAL_BIND:
    @app.middleware("http")
    async def require_api_token(request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        token = request.headers.get("x-token", "")
        if not token or not secrets.compare_digest(token, SIMORGH_KEY or ""):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


origins = [
    o.strip()
    for o in os.getenv(
        "SIMORGH_CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

from core.understanding import UnderstandingEngine
from core.memory import MemoryEngine
from core.why_engine import WhyEngine
from agents.agent_manager import AgentManager
from core.chat import ask as chat_ask
from core.orchestration import Orchestrator

understanding = UnderstandingEngine()
memory = MemoryEngine()
why_engine = WhyEngine()
agent_manager = AgentManager()
orchestrator = Orchestrator()


@app.get("/")
async def root_app():
    app_html = Path(__file__).resolve().parent / "app" / "index.html"
    if not app_html.is_file():
        raise HTTPException(404, "SIMORGH web app not found")
    return FileResponse(app_html)


@app.post("/ask")
async def ask(request: Request, query: str = Form(...)):
    try:
        intent = understanding.detect_intent(query)
        goal, obstacle = understanding.extract_goal_obstacle(query)
        cause = why_engine.find_cause(obstacle) if obstacle else None
        response, ai_generated = agent_manager.consult(
            goal,
            obstacle,
            cause,
            query,
            return_metadata=True,
        )
        memory.store_conversation(
            _session_id(request),
            query,
            response,
            {
                "intent": intent,
                "goal": goal,
                "obstacle": obstacle,
                "cause": cause,
                "ai_generated": ai_generated,
            },
        )
        payload = {
            "response": response,
            "goal": goal,
            "obstacle": obstacle,
            "cause": cause,
            "intent": intent,
            "ai_generated": ai_generated,
            "disclosure": AI_DISCLOSURE if ai_generated else KNOWLEDGE_DISCLOSURE,
            "ai_disclosure": AI_DISCLOSURE if ai_generated else None,
            "knowledge_disclosure": KNOWLEDGE_DISCLOSURE if not ai_generated else None,
        }
        return JSONResponse(
            content=payload,
            headers={"X-SIMORGH-AI-GENERATED": str(ai_generated).lower()},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("ask failed")
        raise HTTPException(500, "Request processing failed") from exc


@app.post("/chat")
async def chat(request: Request, query: str = Form(...), agent: str = Form("hakim")):
    try:
        response, ai_generated = chat_ask(query, agent=agent, return_metadata=True)
        memory.store_conversation(_session_id(request), query, response, {"agent": agent, "ai_generated": ai_generated})
        payload = {
            "response": response,
            "agent": agent,
            "ai_generated": ai_generated,
            "disclosure": AI_DISCLOSURE if ai_generated else KNOWLEDGE_DISCLOSURE,
            "ai_disclosure": AI_DISCLOSURE if ai_generated else None,
            "knowledge_disclosure": KNOWLEDGE_DISCLOSURE if not ai_generated else None,
        }
        return JSONResponse(
            content=payload,
            headers={"X-SIMORGH-AI-GENERATED": str(ai_generated).lower()},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("chat failed")
        raise HTTPException(500, "Chat processing failed") from exc


@app.post("/orchestrate")
async def orchestrate(request: Request, query: str = Form(...)):
    try:
        result = orchestrator.run(query, max_agents=2)
        review_approved = bool(result.get("review", {}).get("approved"))
        response = result.get("final_output", "")
        public_outputs = result.get("outputs", {}) if review_approved else {}
        memory.store_conversation(
            _session_id(request),
            query,
            response,
            {
                "mode": "orchestrated",
                "selected_agents": result["selected_agents"],
                "review": result["review"],
            },
        )
        ai_generated = any(
            bool(value) for value in result.get("ai_generated", {}).values()
        )
        payload = {
            **result,
            "outputs": public_outputs,
            "response": response,
            "ai_generated": ai_generated,
            "disclosure": AI_DISCLOSURE if ai_generated else KNOWLEDGE_DISCLOSURE,
            "ai_disclosure": AI_DISCLOSURE if ai_generated else None,
            "knowledge_disclosure": KNOWLEDGE_DISCLOSURE if not ai_generated else None,
        }
        return JSONResponse(
            content=payload,
            headers={"X-SIMORGH-AI-GENERATED": str(ai_generated).lower()},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("orchestration failed")
        raise HTTPException(500, "Orchestration failed") from exc


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
    for name, port in [("simorgh-core", PORT), ("simorgh-persona", 8001), ("llama-server", 8080)]:
        try:
            r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=2)
            up = r.stdout.strip() == "active"
        except Exception:
            up = False
        services.append({"name": name, "port": port, "up": up})
    return {
        "cpu": psutil.cpu_percent(interval=0.1),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "services": services,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": app.version, "python_version": os.sys.version.split()[0]}


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
