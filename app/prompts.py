"""프롬프트 · LLM 지시 · 컨텍스트 구성 정책 (중앙 관리).

여기 상수/함수만 수정하면 답변 스타일·톤·근거 정책·컨텍스트 캡을 일괄 변경할 수 있다.
(수치 문장 표현은 app/templates.py, 검색·조회 로직은 app/tables_lookup.py·retriever.py)
"""
from __future__ import annotations

import re

# ── 근거 없음 표준 문구 (CLAUDE.md §1.3) ──
NO_EVIDENCE = "규정에 명시되어 있지 않습니다."

# ── 답변 스타일 4종(mode) ──
ANSWER_MODES = {
    "table": "구조화 테이블(SQLite) 조회 — 정밀 수치, LLM 미사용(환각 0)",
    "llm": "설명형 — 근거 컨텍스트로 HCX-30B 생성",
    "context_only": "게이트웨이 미연결 — 자동요약 없이 근거 원문 제시(상담사 확인 유도)",
    "none": f"근거 없음 — '{NO_EVIDENCE}'",
}

# ── 시스템 프롬프트: 상담사 톤 + 근거만 + 출처 + 모르면 모른다 ──
SYSTEM_PROMPT = (
    "너는 우리캐피탈 오토운영팀 상담사를 돕는 보조다. 정중하고 간결한 상담사 말투로 답한다. "
    "반드시 제공된 근거에 근거해서만 답하라. 근거에 없는 수치/사실은 절대 지어내지 말고 "
    f"'{NO_EVIDENCE}'라고 답하라. 답변 끝에 출처(문서명·유효일자)를 밝혀라."
)

# ── 컨텍스트 구성 정책 ──
# 원칙: 정밀 수치는 구조화 테이블이 1차, 원문 청크는 설명 보조. 근거 밖 생성 금지.
CONTEXT_PRINCIPLE = "수치=구조화 테이블 1차 / 설명=원문 청크 보조. 근거 밖 생성 금지."
MAX_CONTEXT_CHUNKS = 4      # 입력 컨텍스트 캡(건수)
MAX_CONTEXT_CHARS = 800     # 청크당 최대 길이(토큰 절약)
MIN_CONTEXT_SCORE = 0.0     # 저점수 근거 컷(임계). 실 임베딩 전환 시 상향 권장(예: 0.35)


def select_contexts(contexts: list[dict]) -> list[dict]:
    """저점수 컷 + 건수 캡 적용."""
    kept = [c for c in contexts if c.get("score", 1.0) >= MIN_CONTEXT_SCORE]
    return kept[:MAX_CONTEXT_CHUNKS]


def lexical_relevant(query: str, contexts: list[dict]) -> bool:
    """질의 의미 토큰(2자↑)이 상위 근거에 하나라도 등장하는지(무관 질의 차단).

    오프라인 폴백 임베딩은 코사인이 무관 질의와도 비슷(0.3~0.4)해 신뢰 불가 →
    어휘 중첩으로 무관 질의를 걸러 '모름' 반환.
    """
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", query)
    if not tokens:
        return False
    joined = " ".join(c.get("text", "") for c in contexts[:MAX_CONTEXT_CHUNKS])
    return any(t in joined for t in tokens)


def build_messages(query: str, contexts: list[dict]) -> list[dict]:
    """설명형 LLM 호출용 messages 구성(시스템 프롬프트 + 근거 컨텍스트)."""
    ctx = "\n\n".join(f"[근거{i + 1}] {c['text'][:MAX_CONTEXT_CHARS]}"
                      for i, c in enumerate(select_contexts(contexts)))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"질문: {query}\n\n근거:\n{ctx}"},
    ]
