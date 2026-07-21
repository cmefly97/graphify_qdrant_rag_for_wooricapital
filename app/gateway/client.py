"""사내 게이트웨이(namc-aigw) 클라이언트.

- HyperCLOVA X / Qwen chat, Octen 임베딩 호출.
- 재시도(지수 백오프)·타임아웃·임베딩 캐시 포함(CLAUDE.md §5).
- 게이트웨이 미연결 시(키 없음/네트워크 오류) ALLOW_OFFLINE_FALLBACK 이면
  결정적 폴백 임베딩을 반환해 로컬/CI 에서도 파이프라인이 동작하게 한다.
  ※ 폴백은 개발용이며, 운영에서는 반드시 키를 설정해 실제 임베딩을 사용한다.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from app.config import Settings, get_settings


class GatewayUnavailable(RuntimeError):
    """게이트웨이 호출 불가(키 없음/네트워크) 이고 폴백도 비활성일 때."""


class GatewayClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.s = settings or get_settings()
        self._emb_cache: dict[str, list[float]] = {}

    # ---------- 내부 유틸 ----------
    def _post(self, url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        last_exc: Exception | None = None
        for attempt in range(self.s.gateway_max_retries):
            try:
                r = httpx.post(url, json=payload, headers=headers, timeout=self.s.gateway_timeout)
                r.raise_for_status()
                return r.json()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                time.sleep(min(2 ** attempt, 8))
        raise GatewayUnavailable(str(last_exc))

    @staticmethod
    def _fallback_embedding(text: str, dim: int = 256) -> list[float]:
        """해시 기반 결정적 임베딩(개발용). 같은 입력→같은 벡터."""
        vec = [0.0] * dim
        for token in text.split():
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    # ---------- 공개 API ----------
    def embed(self, text: str) -> list[float]:
        if text in self._emb_cache:
            return self._emb_cache[text]
        if not self.s.has_embedding_key:
            if self.s.allow_offline_fallback:
                v = self._fallback_embedding(text)
                self._emb_cache[text] = v
                return v
            raise GatewayUnavailable("EMBEDDING_API_KEY 미설정")
        try:
            data = self._post(self.s.embedding_base_url,
                              {"input": text, "model": self.s.embedding_model},
                              self.s.embedding_api_key)
            v = data["data"][0]["embedding"]
        except GatewayUnavailable:
            if self.s.allow_offline_fallback:
                v = self._fallback_embedding(text)
            else:
                raise
        self._emb_cache[text] = v
        return v

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """여러 텍스트를 한 번의 요청으로 임베딩(게이트웨이가 list input 지원 시).

        실패 시 개별 폴백. 252개 순차 호출을 수십 분의 1로 줄인다.
        """
        if not self.s.has_embedding_key:
            if self.s.allow_offline_fallback:
                return [self._fallback_embedding(t) for t in batch]
            raise GatewayUnavailable("EMBEDDING_API_KEY 미설정")
        try:
            data = self._post(self.s.embedding_base_url, {"input": batch, "model": self.s.embedding_model},
                              self.s.embedding_api_key)
            items = sorted(data["data"], key=lambda d: d.get("index", 0))
            return [it["embedding"] for it in items]
        except GatewayUnavailable:
            # 키가 있는데 배치가 실패하면(배치 미지원 가능성) 개별 호출로 재시도 → 실제 임베딩 유지.
            # 키가 없을 때만 폴백(가짜 임베딩)으로 떨어진다.
            if self.s.has_embedding_key:
                return [self.embed(t) for t in batch]
            if self.s.allow_offline_fallback:
                return [self._fallback_embedding(t) for t in batch]
            raise

    def embed_many(self, texts: list[str], batch_size: int = 32, progress=None) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            out.extend(self._embed_batch(texts[start:start + batch_size]))
            if progress:
                progress(min(start + batch_size, len(texts)), len(texts))
        return out

    def chat(self, messages: list[dict[str, str]], model: str | None = None,
             temperature: float = 0.0, max_tokens: int | None = None) -> str:
        if not self.s.has_gateway_key:
            raise GatewayUnavailable("HCX30_API_KEY 미설정 — chat 은 폴백 불가(환각 방지)")
        data = self._post(self.s.hcx30_base_url, {
            "model": model or self.s.hcx30_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.s.answer_max_tokens,
            "chat_template_kwargs": {"thinking": self.s.hcx30_thinking},
        }, self.s.hcx30_api_key)
        return self._extract_content(data)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """다양한 응답 스키마에서 답변 텍스트를 견고하게 추출.

        - 표준 OpenAI 호환: choices[0].message.content
        - reasoning 모델(content=null): choices[0].message.reasoning_content
        - 레거시: choices[0].text
        실패 시 응답 일부를 담아 에러를 던져 원인 파악을 돕는다.
        """
        choices = data.get("choices")
        if not choices:
            raise GatewayUnavailable(f"응답에 'choices' 없음: {str(data)[:300]}")
        first = choices[0] or {}
        msg = first.get("message") or {}
        content = msg.get("content") or msg.get("reasoning_content") or first.get("text")
        if not content:
            raise GatewayUnavailable(f"답변 content 비어있음: {str(first)[:300]}")
        return content
