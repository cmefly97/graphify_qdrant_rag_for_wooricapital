"""앱 설정 — .env 에서만 로드. 키는 코드에 하드코딩하지 않는다(CLAUDE.md §1.6)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM: HCX-30B-Text (사내 게이트웨이 · OpenAI 호환 · thinking)
    hcx30_base_url: str = "http://223.130.140.68:8000/v1/chat/completions"
    hcx30_api_key: str = ""
    hcx30_model: str = "hcx-agent-06"
    qwen_base_url: str = "http://223.130.140.218:8000/v1/chat/completions"
    qwen_model: str = "Qwen3.6-35B-A3B"

    # Embedding (Octen · 사내 vLLM)
    embedding_base_url: str = "http://223.130.140.218:8002/v1/embeddings"
    embedding_api_key: str = ""
    embedding_model: str = "Octen-Embedding-8B"

    # Infra
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "woori_auto"
    embedding_dim: int = 4096  # Octen 기본 차원(실제 적재 시 벡터 길이로 자동 보정)

    # Options
    allow_offline_fallback: bool = True
    gateway_timeout: int = 30
    gateway_max_retries: int = 3
    answer_max_tokens: int = 2048  # 답변 최대 토큰(잘림 방지). .env ANSWER_MAX_TOKENS 로 조정

    @property
    def has_gateway_key(self) -> bool:
        """HCX-30B chat 사용 가능 여부."""
        return bool(self.hcx30_api_key) and not self.hcx30_api_key.startswith("sk-your")

    @property
    def has_embedding_key(self) -> bool:
        """Octen 임베딩 사용 가능 여부(미설정 시 폴백 임베딩)."""
        return bool(self.embedding_api_key) and not self.embedding_api_key.startswith("sk-your")


@lru_cache
def get_settings() -> Settings:
    return Settings()
