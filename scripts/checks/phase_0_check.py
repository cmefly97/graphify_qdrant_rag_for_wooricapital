"""phase_0 커스텀 검증 — 게이트웨이/인프라 설정 점검.

산출물이 아직 없으면 통과(skip)하여 구현 전 단계를 방해하지 않는다.
"""
from __future__ import annotations

from pathlib import Path

REQUIRED_ENV_KEYS = [
    "HCX30_BASE_URL", "HCX30_API_KEY", "HCX30_MODEL",
    "EMBEDDING_MODEL", "QDRANT_URL",
]


def check(root: Path) -> list[dict]:
    results: list[dict] = []

    env_example = root / ".env.example"
    if env_example.exists():
        text = env_example.read_text(encoding="utf-8")
        missing = [k for k in REQUIRED_ENV_KEYS if k not in text]
        results.append({
            "name": "env_keys",
            "ok": not missing,
            "detail": ("누락 키: " + ", ".join(missing)) if missing else "필수 게이트웨이 키 모두 존재",
            "blocking": True,
        })

    compose = root / "docker-compose.yml"
    if compose.exists():
        text = compose.read_text(encoding="utf-8").lower()
        ok = "qdrant" in text
        results.append({
            "name": "compose_qdrant",
            "ok": ok,
            "detail": "qdrant 서비스 정의됨" if ok else "docker-compose 에 qdrant 서비스 없음",
            "blocking": True,
        })

    # 시크릿이 .env.example 에 실제 키처럼 박혀있지 않은지(플레이스홀더 여부)
    if env_example.exists():
        text = env_example.read_text(encoding="utf-8")
        leaked = "sk-" in text and "sk-your" not in text and "sk-xxxx" not in text
        results.append({
            "name": "no_real_secret",
            "ok": not leaked,
            "detail": "실제 키로 의심되는 값" if leaked else "플레이스홀더만 존재",
            "blocking": True,
        })

    return results
