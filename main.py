from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os
import subprocess
import psutil
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

app = FastAPI()
from core.voice_docs import router as voice_docs_router
app.include_router(voice_docs_router)
from core.dashboard_api import router as dashboard_api_router
app.include_router(dashboard_api_router)
from core.voice_endpoint import router as voice_endpoint_router
app.include_router(voice_endpoint_router)

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
async def chat(query: str = Form(...), agent: str = Form("hakim")):
    try:
        logger.info(f"Chat query: {query} (agent={agent})")
        response = chat_ask(query, agent=agent)
        return {"response": response, "agent": agent}
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
    return FileResponse("/home/mahdi/Desktop/simorgh_dashboard.html")


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
    return {
        "cpu": psutil.cpu_percent(interval=0.3),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "services": services,
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "python_version": f"{Path('/usr/bin/python3.11').resolve()}"
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
