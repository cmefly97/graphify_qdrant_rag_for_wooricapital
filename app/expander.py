"""쿼리 확장 — 동의어·영문·유사표현 생성으로 예시 밖 질문 대응.

오프라인 사전 + (옵션) LLM 확장. 키워드 불일치로 검색이 누락되는 그래프RAG
약점을 보완한다.
"""
from __future__ import annotations

SYNONYMS: dict[str, list[str]] = {
    "금리": ["이자율", "rate", "G/L금리"],
    "네고": ["nego", "조정금리", "할인"],
    "취급": ["가능", "승인", "한도"],
    "개월": ["기간", "term", "개월수"],
    "슬라이딩": ["sliding", "수수료 차감"],
    "R판정": ["취급불가", "필터링", "개인회생", "신용회복"],
    "듀얼": ["dual", "Dual_C", "Dual_O"],
    "엔카": ["encar", "엔카_Zero"],
}


def expand(query: str) -> list[str]:
    variants = {query}
    for key, syns in SYNONYMS.items():
        if key in query:
            for s in syns:
                variants.add(query.replace(key, s))
    return list(variants)
