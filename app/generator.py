"""답변 생성 — 근거 기반, 수치는 테이블 결과 우선, 근거 없으면 '모름'.

정책(프롬프트·컨텍스트 캡·근거 게이트)은 app/prompts.py, 문구는 app/templates.py 에서 관리.
"""
from __future__ import annotations

from app import prompts, templates
from app.gateway.client import GatewayClient, GatewayUnavailable


def generate(query: str, route: str, table_result: dict | None,
             contexts: list[dict], gc: GatewayClient) -> dict:
    # 1) 수치/규칙형: 테이블 정답 우선(LLM 미사용 → 환각 0)
    if table_result:
        return {"answer": table_result["answer"], "sources": table_result.get("sources", []),
                "mode": "table", "confidence": "high"}

    # 2) 근거 없음 또는 어휘적으로 무관 → '모름'
    if not contexts or not prompts.lexical_relevant(query, contexts):
        return {"answer": prompts.NO_EVIDENCE, "sources": [], "mode": "none", "confidence": "low"}

    # 3) 설명형: 게이트웨이 있으면 LLM, 없으면 근거 원문 제시(환각 방지)
    sources = [c.get("source", {}) for c in prompts.select_contexts(contexts)[:3]]
    if gc.s.has_gateway_key:
        try:
            answer = gc.chat(prompts.build_messages(query, contexts))
            return {"answer": answer, "sources": sources, "mode": "llm", "confidence": "medium"}
        except GatewayUnavailable:
            pass
    return {"answer": templates.context_only(contexts[0]["text"]),
            "sources": sources, "mode": "context_only", "confidence": "medium"}
