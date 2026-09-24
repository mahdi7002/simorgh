from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Thread

from fastapi import FastAPI
from fastapi.responses import FileResponse

from core.mother.api import router as mother_router
from core.mother.service import MotherService

PORT = int(os.environ.get("SIMORGH_MOTHER_PORT", "8010"))
HOST = os.environ.get("SIMORGH_MOTHER_HOST", "127.0.0.1")
SERVICE = MotherService(int(os.environ.get("SIMORGH_MOTHER_INTERVAL_SECONDS", "300")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = Thread(target=SERVICE.start, name="simorgh-mother-observer", daemon=True)
    thread.start()
    try:
        yield
    finally:
        SERVICE._stop = True
        thread.join(timeout=10)


app = FastAPI(title="SIMORGH Mother", version="1.0.0", lifespan=lifespan)
app.include_router(mother_router)


@app.get("/")
def root():
    page = Path(__file__).resolve().parents[2] / "app" / "mother.html"
    return FileResponse(page)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "simorgh-mother", "port": PORT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
