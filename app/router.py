"""질의 라우터 — 수치형 / 설명형 / 혼합형 분류.

오프라인에서도 동작하도록 키워드 휴리스틱을 1차로 쓰고,
게이트웨이가 있으면 LLM 분류로 보강할 수 있다(여기서는 휴리스틱).
"""
from __future__ import annotations

import re

NUMERIC_HINTS = ("금리", "등급", "개월", "한도", "금액", "점", "%", "네고", "nego", "이자율")
RULE_HINTS = ("가능", "까지", "판정", "슬라이딩", "대상", "여부", "취급")


def classify(query: str) -> str:
    q = query.lower()
    has_num = any(h.lower() in q for h in NUMERIC_HINTS) or bool(re.search(r"\d", q))
    has_rule = any(h in query for h in RULE_HINTS)
    if has_num and has_rule:
        return "mixed"
    if has_num:
        return "numeric"
    return "descriptive"
