"""구조화 테이블 조회 — 정밀 수치의 유일한 출처(CLAUDE.md §1.1).

자연어 질의를 파라미터로 변환해 data/tables.db 를 조회하고, 환각 없는
답변 문장과 출처를 만든다. 조회 불가 시 None(→ 설명형 경로 또는 '모름').
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app import templates

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tables.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _src(row: dict) -> dict:
    return {"source_file": row.get("source_file"), "effective_date": row.get("effective_date")}


def _nice_grade(query: str, con: sqlite3.Connection) -> int | None:
    m = re.search(r"(\d{3})\s*점", query)
    if not m:
        return None
    score = int(m.group(1))
    r = con.execute("SELECT nice_grade FROM nice_band WHERE ? BETWEEN score_min AND score_max",
                    (score,)).fetchone()
    return r["nice_grade"] if r else None


def lookup_rate(query: str) -> dict | None:
    m = re.search(r"(\d+)\s*등급", query)
    if not ("금리" in query and m):
        return None
    grade = int(m.group(1))
    ctype = "외국인" if "외국인" in query else "내국인"
    tm = re.search(r"(\d+)\s*개월", query)
    con = _conn()
    if tm:  # 구간(개월) 지정 시 해당 구간 우선
        rg = con.execute(
            "SELECT * FROM rate_grade WHERE customer_type=? AND grade=? AND term_min_months<=? "
            "ORDER BY term_min_months DESC LIMIT 1", (ctype, grade, int(tm.group(1)))).fetchone()
    else:
        rg = None
    if not rg:
        rg = con.execute(
            "SELECT * FROM rate_grade WHERE customer_type=? AND grade=? ORDER BY term_min_months LIMIT 1",
            (ctype, grade)).fetchone()
    if not rg:
        con.close()
        return None
    negos = {r["authority"]: r for r in con.execute(
        "SELECT * FROM nego_rule WHERE customer_type=? AND grade_from<=? AND grade_to>=?",
        (ctype, grade, grade)).fetchall()}
    niceg = _nice_grade(query, con)
    con.close()

    internal = negos.get("internal")
    internal_cond = internal["nice_condition"] if internal else None
    extra = [templates.nego_extra(label, negos[a]["nego_rate"])
             for a, label in (("거점장", "거점장"), ("증빙", "증빙"), ("HJ", "HJ"))
             if negos.get(a) and negos[a]["nego_rate"]]
    answer = templates.rate_answer(grade, rg["gl_rate"], niceg, internal_cond, extra, ctype)
    return {"answer": answer, "structured": {"grade": grade, "gl_rate": rg["gl_rate"],
            "customer_type": ctype, "nice_grade": niceg},
            "sources": [_src(dict(rg))]}


def lookup_condition(query: str) -> dict | None:
    q = query.lower()
    con = _conn()
    res = None
    if "개월" in query and any(k in query for k in ("취급", "론", "할부", "기간")):
        r = con.execute("SELECT * FROM condition_rule WHERE attribute='취급개월수' LIMIT 1").fetchone()
        if r:
            res = {"answer": f"{r['product']} 취급 가능 개월수는 {r['value']} 입니다.",
                   "structured": dict(r), "sources": [_src(dict(r))]}
    elif "듀얼" in query or "dual" in q:
        rows = con.execute("SELECT * FROM condition_rule WHERE attribute LIKE '금리등급상한%'").fetchall()
        if rows:
            lines = [f"{r['product']} {('내국인' if '내국인' in r['attribute'] else '외국인')} {r['value']}등급" for r in rows]
            res = {"answer": "듀얼상품 금리등급 취급 상한: " + ", ".join(lines) + " 까지.",
                   "structured": [dict(r) for r in rows], "sources": [_src(dict(rows[0]))]}
    elif "엔카" in query:
        r = con.execute("SELECT * FROM condition_rule WHERE product='엔카 슬라이딩' LIMIT 1").fetchone()
        if r:
            res = {"answer": f"엔카 슬라이딩은 {r['value']}합니다. 조건: {r['condition']}",
                   "structured": dict(r), "sources": [_src(dict(r))]}
    elif "r판정" in q or "개인회생" in query or "신용회복" in query:
        r = con.execute("SELECT * FROM condition_rule WHERE attribute='판정값_R' LIMIT 1").fetchone()
        if r:
            res = {"answer": f"판정값이 R판정인 경우 '{r['value']}' 대상입니다.",
                   "structured": dict(r), "sources": [_src(dict(r))]}
    con.close()
    return res


def lookup_residual_group(query: str) -> dict | None:
    """중고리스 잔가군 조회 — 질의의 차종명이 어느 잔가군에 속하는지."""
    if not any(k in query for k in ("잔가군", "잔가", "어느 군", "무슨 군")):
        return None
    tokens = [t for t in re.findall(r"[가-힣A-Za-z0-9]{2,}", query)
              if t not in ("잔가군", "잔가", "차량", "차종", "어느", "무슨", "알려줘", "뭐야")]
    con = _conn()
    hit = None
    for tok in tokens:
        r = con.execute("SELECT grp, maker, models, source_file FROM lease_residual_group "
                        "WHERE models LIKE ? LIMIT 1", (f"%{tok}%",)).fetchone()
        if r:
            hit = (tok, r)
            break
    con.close()
    if not hit:
        return None
    tok, r = hit
    return {"answer": f"중고리스 잔가군 기준 '{tok}' 차량은 {r['maker']} {r['grp']}에 해당합니다.",
            "structured": {"model_query": tok, "maker": r["maker"], "group": r["grp"]},
            "sources": [{"source_file": r["source_file"], "effective_date": "2026-03"}]}


_STOP = {"알려줘", "뭐야", "어떻게", "되나요", "가능해", "인가요", "얼마나", "필요해", "관련",
         "조건", "기준", "정보", "내국인", "외국인"}  # 고객유형 수식어는 단독 매칭 방지


def lookup_nego_overview(query: str) -> dict | None:
    """'네고 조건' 류(특정 등급 없음) → 금리등급별 기준 네고 요약(nego_rule)."""
    if "네고" not in query and "nego" not in query.lower():
        return None
    if re.search(r"(\d+)\s*등급", query):  # 특정 등급 지정 시 lookup_rate 가 처리
        return None
    if "IRR" in query.upper() or "중고리스" in query or "리스" in query:  # 리스 IRR 네고는 별도 처리
        return None
    ctype = "외국인" if "외국인" in query else "내국인"
    con = _conn()
    internal = con.execute(
        "SELECT grade_from AS g, nice_condition FROM nego_rule "
        "WHERE customer_type=? AND authority='internal' ORDER BY grade_from", (ctype,)).fetchall()
    auth = con.execute(
        "SELECT DISTINCT authority, nego_rate FROM nego_rule "
        "WHERE customer_type=? AND authority IN ('거점장','증빙','HJ') AND nego_rate IS NOT NULL", (ctype,)).fetchall()
    con.close()
    if not internal:
        return None
    grade_map = ", ".join(f"{r['g']}등급 {r['nice_condition']}" for r in internal if r["nice_condition"])
    auth_txt = ", ".join(sorted({f"{r['authority']} {r['nego_rate']}" for r in auth}))
    answer = templates.nego_overview(ctype, grade_map, auth_txt)
    return {"answer": answer,
            "structured": {"customer_type": ctype, "internal": [dict(r) for r in internal]},
            "sources": [{"source_file": "9_샘플_중고승용 상품운영기준.pdf", "effective_date": "2026-03"}]}


def lookup_condition_generic(query: str) -> dict | None:
    """범용 조건 조회 — 질의 토큰과 condition_rule(상품·속성·값·조건) 어휘 중첩 점수."""
    tokens = [t for t in re.findall(r"[가-힣A-Za-z0-9]{2,}", query) if t not in _STOP]
    if not tokens:
        return None
    # 질의에 상품명이 있으면 해당 상품으로 후보를 한정(상품 교차 매칭 방지)
    scope = next((p for p in ("중형트럭", "재고금융", "엔카", "신용구제") if p in query), None)
    if scope:
        # 범위 한정 시 상품명 토큰은 점수에서 제외(값 텍스트의 상품명 언급에 오매칭 방지)
        tokens = [t for t in tokens if t not in scope and scope not in t]
        if not tokens:
            return None
    con = _conn()
    rows = con.execute("SELECT * FROM condition_rule").fetchall()
    con.close()
    if scope:
        rows = [r for r in rows if scope in (r["product"] or "")]
    best, best_score = None, 0
    for row in rows:
        prod, attr = row["product"] or "", row["attribute"] or ""
        val = row["value"] or ""
        product_hit = any(t in prod for t in tokens)
        # 비범위 질의는 상품명이 일치하는 행만 대상 — 흔한 단어 1개(예: '주말') 오매칭 방지
        if not scope and not product_hit:
            continue
        score = 3 if (not scope and product_hit) else 0
        for tok in tokens:
            if tok in attr:
                score += 3   # 속성(질문 주제) 일치를 강하게
            if tok in val:
                score += 1
            # condition(비고/주석)은 매칭 점수에 넣지 않음 — 엉뚱한 행 선택 방지
        if score > best_score:
            best, best_score = row, score
    threshold = 1 if scope else 4  # 비범위는 상품(3)+속성/값(≥1) 이상
    if not best or best_score < threshold:
        return None
    ans = f"{best['product']} {best['attribute']}: {best['value']}"
    if best["condition"]:
        ans += f" (조건/비고: {best['condition']})"
    return {"answer": ans, "structured": dict(best), "sources": [_src(dict(best))]}


def lookup_promotion(query: str) -> dict | None:
    """프로모션·우량고객 금리 기준 조회 + (점수 입력 시) 가능/불가 판정."""
    if "프로모션" not in query and "프로모" not in query:
        return None
    con = _conn()
    rows = con.execute("SELECT * FROM condition_rule WHERE product='프로모션' ORDER BY rowid").fetchall()
    con.close()
    if not rows:
        return None
    main = next((r for r in rows if r["attribute"] == "우량고객 최저금리"), rows[0])
    val = main["value"]  # "... NICE 933점 이상 & KCB 976점 이상일 경우 G/L 금리 7.6% ..."
    nice_req = int(re.search(r"NICE\s*(\d+)", val).group(1)) if re.search(r"NICE\s*(\d+)", val) else None
    kcb_req = int(re.search(r"KCB\s*(\d+)", val).group(1)) if re.search(r"KCB\s*(\d+)", val) else None

    # 질의에서 사용자 점수 추출
    nu = re.search(r"(?:나이스|NICE)\s*(\d{3,4})", query, re.I)
    ku = re.search(r"KCB\s*(\d{3,4})", query, re.I)
    asks = any(k in query for k in ("가능", "되나", "돼", "사용", "적용", "여부"))

    if (nu or ku) and asks and nice_req and kcb_req:
        checks, failed = [], []
        if nu:
            v = int(nu.group(1)); ok = v >= nice_req
            checks.append(f"NICE {v}({'충족' if ok else f'미충족·{nice_req}점 이상 필요'})")
            if not ok:
                failed.append("NICE")
        if ku:
            v = int(ku.group(1)); ok = v >= kcb_req
            checks.append(f"KCB {v}({'충족' if ok else f'미충족·{kcb_req}점 이상 필요'})")
            if not ok:
                failed.append("KCB")
        answer = templates.promotion_judgment(failed, nice_req, kcb_req, checks)
        return {"answer": answer,
                "structured": {"nice_req": nice_req, "kcb_req": kcb_req, "failed": failed},
                "sources": [_src(dict(main))]}

    # 점수 미입력 → 기준 안내
    return {"answer": templates.promotion_criteria([dict(r) for r in rows]),
            "structured": [dict(r) for r in rows], "sources": [_src(dict(main))]}


def lookup_corporate(query: str) -> dict | None:
    """법인 적용금리 조회(대표자 입보/미입보 기준)."""
    if "법인" not in query or ("금리" not in query and "적용" not in query):
        return None
    con = _conn()
    r = con.execute("SELECT * FROM condition_rule WHERE product='법인' AND attribute='적용금리' LIMIT 1").fetchone()
    con.close()
    if not r:
        return None
    return {"answer": r["value"], "structured": dict(r), "sources": [_src(dict(r))]}


# 고유(distinctive) 키워드 → condition_rule 의 attribute/product 로 조회하는 팩트 라우터
_FACT_KEYWORDS = ["연체이자율", "연체", "중도상환", "판촉", "슬라이딩", "금융리스", "IRR", "취급기간",
                  "신청가능", "대출가능", "최대대출", "DB시세", "연식", "대상물품", "카히스토리",
                  "특별승인", "특별 승인", "책임채권", "임직원"]


def lookup_fact(query: str) -> dict | None:
    con = _conn()
    rows = con.execute("SELECT * FROM condition_rule").fetchall()
    con.close()

    def _mk(r):
        ans = f"{r['product']} {r['attribute']}: {r['value']}" + (f" ({r['condition']})" if r["condition"] else "")
        return {"answer": ans, "structured": dict(r), "sources": [_src(dict(r))]}

    for kw in _FACT_KEYWORDS:
        if kw not in query:
            continue
        # 속성(질문 주제) 일치 우선, 없으면 상품명 일치
        for r in rows:
            if kw in (r["attribute"] or ""):
                return _mk(r)
        for r in rows:
            if kw in (r["product"] or ""):
                return _mk(r)
    return None


def lookup(query: str) -> dict | None:
    return (lookup_residual_group(query)
            or lookup_promotion(query)
            or lookup_condition(query)
            or lookup_rate(query)
            or lookup_nego_overview(query)
            or lookup_corporate(query)
            or lookup_condition_generic(query)
            or lookup_fact(query))
