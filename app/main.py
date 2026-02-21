from fastapi import FastAPI

from app.api.departments import router as departments_router
from app.core.logger import configure_logging

configure_logging()

app = FastAPI(title="Org Structure API", version="1.0.0")

app.include_router(departments_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
