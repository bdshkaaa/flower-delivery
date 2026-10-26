import logging
import time

from fastapi import FastAPI, Request
from sqlalchemy import text

from .config import settings
from .db import engine
from .logging_setup import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger("app")

app = FastAPI(title="Flower Delivery API")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логируем метод, путь, статус и время ответа — по этим логам
    проверяем latency из таблицы контрактов API (README, этап 3)."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s in %.1f ms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
