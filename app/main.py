"""FastAPI 진입점. Phase 2 에서 질의 API 라우터를 include 한다."""
from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings

app = FastAPI(title="우리캐피탈 오토운영팀 상담챗봇 API")


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "gateway_key_configured": s.has_gateway_key,
        "offline_fallback": s.allow_offline_fallback,
        "qdrant_url": s.qdrant_url,
    }


from app.api import api_router  # noqa: E402

app.include_router(api_router)
