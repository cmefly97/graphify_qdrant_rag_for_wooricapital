"""답변 표현 · 문장 템플릿 · 표기 정책 (중앙 관리).

수치 값은 항상 tables.db 조회 결과를 그대로 받아 문장으로만 감싼다(계산·생성 금지).
표현/정책을 바꾸려면 이 파일만 수정한다.
"""
from __future__ import annotations

# ── 표기 정책 플래그 ──
SHOW_BOTH_CUSTOMER_TYPES_WHEN_UNSPECIFIED = False  # 미지정 시 내국인 기준(True면 내/외국인 모두 안내)
COMPUTE_MIN_RATE = False   # 최저금리를 산술 계산하지 않음 — 표에 있는 값만 제시
CONTEXT_ONLY_NOTE = "관련 근거를 찾았습니다(자동요약은 게이트웨이 연결 시 제공). 확인 바랍니다:"


def default_customer_type(query: str) -> str:
    return "외국인" if "외국인" in query else "내국인"


def format_sources(rows: list[dict] | dict) -> list[dict]:
    """출처 표기 방식: {source_file, effective_date} dict 리스트로 통일."""
    if isinstance(rows, dict):
        rows = [rows]
    out = []
    for r in rows:
        out.append({"source_file": r.get("source_file"),
                    "effective_date": r.get("effective_date")})
    return out


def source_badge(source: dict) -> str:
    """UI/텍스트용 단일 출처 배지 문자열."""
    sf = source.get("source_file")
    if not sf:
        return ""
    ed = source.get("effective_date")
    return f"[{sf}{' · ' + ed if ed else ''}]"


# ── 금리(rate) 답변 문장 ──
def rate_answer(grade: int, gl_rate: str, nice_grade: int | None,
                internal_cond: str | None, extras: list[str], customer_type: str = "내국인") -> str:
    parts = [f"금리등급 {grade}등급시 {gl_rate} G/L금리"]
    if nice_grade and internal_cond:
        parts.append(f"이며 NICE {nice_grade}등급이므로 {internal_cond} 네고 적용됩니다")
    elif internal_cond:
        parts.append(f"이며 {customer_type} 네고 {internal_cond} 적용됩니다")
    answer = "".join(parts)
    if extras:
        answer += ". 추가로 " + ", ".join(extras) + "가 가능합니다."
    return answer


def nego_extra(label: str, rate: str) -> str:
    return f"{label} 네고 {rate}"


# ── 네고 개요 ──
def nego_overview(customer_type: str, grade_map: str, auth_txt: str) -> str:
    return (f"{customer_type} 금리 네고는 금리등급·NICE등급에 따라 다릅니다. "
            f"등급별 기준 네고: {grade_map}. "
            f"권한별 네고(거점장·증빙·HJ)도 등급 구간에 따라 추가 적용됩니다(예: {auth_txt}).")


# ── 프로모션 ──
def promotion_criteria(rows: list[dict]) -> str:
    lines = [f"{r['attribute']} — {r['value']}" + (f" ({r['condition']})" if r["condition"] else "")
             for r in rows]
    return "프로모션 기준: " + " / ".join(lines)


def promotion_judgment(failed: list[str], nice_req: int, kcb_req: int, checks: list[str]) -> str:
    head = "아니요, 불가능합니다." if failed else "네, (아래 조건 충족 시) 가능합니다."
    tail = "" if failed else " 금리등급 1등급·법인 여부도 함께 확인하세요."
    return (f"{head} 프로모션 G/L 금리 7.6%는 "
            f"금리등급 1등급 & NICE {nice_req}점 이상 & KCB {kcb_req}점 이상 "
            f"세 조건을 모두 충족해야 적용됩니다(법인 제외). 입력값 — {', '.join(checks)}." + tail)


# ── 조건/사실 일반 ──
def condition_line(product: str, attribute: str, value: str, condition: str = "") -> str:
    return f"{product} {attribute}: {value}" + (f" ({condition})" if condition else "")


def context_only(top_text: str) -> str:
    return f"{CONTEXT_ONLY_NOTE}\n{top_text}"
