from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import JSONResponse

app = APIRouter(prefix="/api")


@app.get(
    "/health",
)
async def healthcheck():
    response = JSONResponse(
        {"service": "ok"},
        status_code=200,
    )
    return response
