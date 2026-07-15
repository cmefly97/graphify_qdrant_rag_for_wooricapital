"""구조화 테이블 추출 → data/tables.db (docs/TABLE_SCHEMA.md 스키마).

정밀 수치(금리·등급·네고·조건)는 여기서만 만든다(CLAUDE.md §1.1 환각 금지).
근거 샘플: souce/9_샘플_중고승용 상품운영기준.pdf p.1 (내국인/외국인 금리표).

병합 셀 처리: 증빙·HJ 등 세로 병합 컬럼은 forward-fill, 거점장처럼 등급별
개별값이 있는 컬럼은 fill 하지 않는다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "souce"
DB_PATH = ROOT / "data" / "tables.db"
SUSEUNG_PDF = SOURCE_DIR / "9_샘플_중고승용 상품운영기준.pdf"
LEASE_PDF = SOURCE_DIR / "8_샘플_중고리스 운영기준(변경).pdf"
TRUCK_PDF = SOURCE_DIR / "10_샘플_중형트럭 시범운영기준.pdf"
JAEGO_MD = SOURCE_DIR / "5_재고금융_운영자금심사운영기준.md"
EFFECTIVE = "2026-03-01"


def _schema(cur: sqlite3.Cursor) -> None:
    cur.executescript("""
    DROP TABLE IF EXISTS rate_grade;
    DROP TABLE IF EXISTS nego_rule;
    DROP TABLE IF EXISTS condition_rule;
    DROP TABLE IF EXISTS nice_band;
    DROP TABLE IF EXISTS lease_residual_group;
    CREATE TABLE rate_grade(
      product TEXT, customer_type TEXT, grade INTEGER, term_min_months INTEGER,
      gl_rate TEXT, effective_date TEXT, source_file TEXT, source_page INTEGER);
    CREATE TABLE nego_rule(
      product TEXT, customer_type TEXT, grade_from INTEGER, grade_to INTEGER,
      authority TEXT, nice_condition TEXT, nego_rate TEXT, nego_note TEXT,
      effective_date TEXT, source_file TEXT, source_page INTEGER);
    CREATE TABLE condition_rule(
      product TEXT, attribute TEXT, value TEXT, condition TEXT,
      effective_date TEXT, source_file TEXT);
    CREATE TABLE nice_band(score_min INTEGER, score_max INTEGER, nice_grade INTEGER);
    CREATE TABLE lease_residual_group(
      grp TEXT, maker TEXT, models TEXT, source_file TEXT);
    """)


def _cond(cur, product, attribute, value, condition, source):
    cur.execute("INSERT INTO condition_rule VALUES(?,?,?,?,?,?)",
                (product, attribute, value, condition, EFFECTIVE, source))


def extract_truck(cur: sqlite3.Cursor) -> int:
    """중형트럭 상품조건 표(22x5) → condition_rule."""
    import pdfplumber

    with pdfplumber.open(TRUCK_PDF) as pdf:
        t = pdf.pages[0].extract_tables()[0]
    n = 0
    last_cat = ""
    for r in t[1:]:
        c = [(x or "").replace("\n", " ").strip() for x in r]
        cat = c[0] or last_cat
        last_cat = cat
        label = c[1]
        detail = c[3] if len(c) > 3 else ""
        note = c[4] if len(c) > 4 else ""
        if not detail:
            continue
        attribute = f"{cat}/{label}" if label else cat
        _cond(cur, "중형트럭", attribute, detail, note, TRUCK_PDF.name)
        n += 1
    return n


def extract_lease_residual_groups(cur: sqlite3.Cursor) -> int:
    """중고리스 잔가군(S~V) 차종 분류표(p5 t0,t1) → lease_residual_group."""
    import pdfplumber

    n = 0
    with pdfplumber.open(LEASE_PDF) as pdf:
        tables = pdf.pages[4].extract_tables()
    for t in tables[:2]:
        groups = [(c or "").replace("\n", " ").strip() for c in t[0][2:]]  # S군, A군 ...
        for r in t[1:]:
            cells = [(c or "").replace("\n", " ").strip() for c in r]
            maker = cells[1]
            if not maker:
                continue
            for gi, grp in enumerate(groups):
                models = cells[2 + gi] if 2 + gi < len(cells) else ""
                if grp and models:
                    cur.execute("INSERT INTO lease_residual_group VALUES(?,?,?,?)",
                                (grp, maker, models, LEASE_PDF.name))
                    n += 1
    return n


def extract_jaego(cur: sqlite3.Cursor) -> int:
    """재고금융/운영자금 핵심 규칙 → condition_rule (md 본문 근거)."""
    rules = [
        ("재고금융", "대상상품", "중고차 재고금융 / 중고차 운영자금 / 수입차 재고금융", "제2조 적용범위"),
        ("재고금융", "대상물품", "연식 10년 이내 국산/수입 순수승용차, 2.5톤 미만 화물차, 15인승 이하 승합차",
         "특장차/특수차량/영업용차량 제외"),
        ("재고금융", "대상고객", "사업자등록·업력·매출·판매대수 증빙 가능한 개인사업자/법인", "수입차 재고금융은 법인만"),
        ("재고금융", "채권서류 발급기한", "대출신청일 기준 1개월 이내", "법인인감은 3개월까지 가능"),
        ("재고금융", "취급제한", "최근 6개월내 30일 이상 연체경험자", "취급불가 대상"),
    ]
    for product, attr, val, cond in rules:
        _cond(cur, product, attr, val, cond, JAEGO_MD.name)
    return len(rules)


def extract_suseung_naegukin(cur: sqlite3.Cursor) -> int:
    """내국인 금리표(표1): 등급별 GL금리 + 거점장/증빙/HJ 네고(병합 처리)."""
    import pdfplumber

    with pdfplumber.open(SUSEUNG_PDF) as pdf:
        t = pdf.pages[0].extract_tables()[1]  # 내국인
    last = {"geo": None, "jeung": None, "hj": None}
    n = 0
    for r in t[3:]:
        g = (r[0] or "").strip()
        if not g.isdigit():
            continue
        grade = int(g)
        gl = (r[1] or "").strip()
        internal = (r[2] or "").replace("\n", " ").strip()
        geo = (r[3] or "").strip() or last["geo"]; last["geo"] = geo
        jeung = (r[4] or "").strip() or last["jeung"]; last["jeung"] = jeung
        hj = (r[5] or "").strip() or last["hj"]; last["hj"] = hj
        cur.execute("INSERT INTO rate_grade VALUES(?,?,?,?,?,?,?,?)",
                    ("중고승용 론/할부", "내국인", grade, 12, gl, EFFECTIVE, SUSEUNG_PDF.name, 1))
        for authority, val in (("internal", internal), ("거점장", geo), ("증빙", jeung), ("HJ", hj)):
            rate = val if val and "%" in val else None
            cur.execute("INSERT INTO nego_rule VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        ("중고승용 론/할부", "내국인", grade, grade, authority,
                         val if authority == "internal" else None, rate, val,
                         EFFECTIVE, SUSEUNG_PDF.name, 1))
        n += 1
    return n


def extract_suseung_foreigner(cur: sqlite3.Cursor) -> int:
    """외국인 금리표(표2): 등급 × 구간(12/24/36/48개월)별 GL금리 → rate_grade."""
    import pdfplumber

    with pdfplumber.open(SUSEUNG_PDF) as pdf:
        t = pdf.pages[0].extract_tables()[2]  # 외국인
    terms = [12, 24, 36, 48]
    n = 0
    for r in t:
        g = (r[0] or "").strip()
        if not g.isdigit():
            continue
        grade = int(g)
        for col, term in enumerate(terms, start=1):
            gl = (r[col] or "").strip()
            if gl and "%" in gl:
                cur.execute("INSERT INTO rate_grade VALUES(?,?,?,?,?,?,?,?)",
                            ("중고승용 론/할부", "외국인", grade, term, gl, EFFECTIVE, SUSEUNG_PDF.name, 1))
                n += 1
    return n


def seed_condition_rules(cur: sqlite3.Cursor) -> None:
    """예시 질의 대응 조건 규칙(샘플). 운영에서는 파서로 자동 추출/확장."""
    rules = [
        ("론/할부", "취급개월수", "12~72개월", "", EFFECTIVE, SUSEUNG_PDF.name),
        ("Dual_C", "금리등급상한_내국인", "7", "", EFFECTIVE, SUSEUNG_PDF.name),
        ("Dual_C", "금리등급상한_외국인", "7", "", EFFECTIVE, SUSEUNG_PDF.name),
        ("Dual_O", "금리등급상한_내국인", "7", "", EFFECTIVE, SUSEUNG_PDF.name),
        ("Dual_O", "금리등급상한_외국인", "7", "", EFFECTIVE, SUSEUNG_PDF.name),
        ("엔카 슬라이딩", "가능여부", "조건부 가능",
         "국산/수입 & 19년식 이내 & 주행 연평균500만km 이하 & 카히스토리 사고33백만원 이내 & 특수사고(전손/침수/도난/부활) 없음",
         EFFECTIVE, SUSEUNG_PDF.name),
        ("신용구제", "판정값_R", "필터링 취급 불가", "신용회복/개인회생 R판정", EFFECTIVE, SUSEUNG_PDF.name),
    ]
    cur.executemany("INSERT INTO condition_rule VALUES(?,?,?,?,?,?)", rules)
    # NICE 점수(이상)→금리등급 (9_중고승용 원문 실제값). score_min 이상 ~ score_max 이하.
    cur.executemany("INSERT INTO nice_band VALUES(?,?,?)", [
        (933, 1000, 1), (884, 932, 2), (846, 883, 3), (812, 845, 4), (769, 811, 5),
        (709, 768, 6), (669, 708, 7), (610, 668, 8), (350, 609, 9),
    ])


def extract_promotion(cur: sqlite3.Cursor) -> int:
    """중고승용 프로모션·우량고객 금리 기준 → condition_rule (9_중고승용 pdf 본문 근거)."""
    rules = [
        ("프로모션", "우량고객 최저금리",
         "금리등급 1등급 & NICE 933점 이상 & KCB 976점 이상일 경우 G/L 금리 7.6% 적용", "법인 제외",
         EFFECTIVE, SUSEUNG_PDF.name),
        ("프로모션", "주말·공휴일 인하", "금리 1~6등급 최대 0.5% 인하 가능", "주말(공휴일) 진행건",
         EFFECTIVE, SUSEUNG_PDF.name),
        ("프로모션", "최저금리", "5.9%", "", EFFECTIVE, SUSEUNG_PDF.name),
    ]
    cur.executemany("INSERT INTO condition_rule VALUES(?,?,?,?,?,?)", rules)
    return len(rules)


def extract_corporate(cur: sqlite3.Cursor) -> int:
    """법인 적용금리 기준 → condition_rule (8_중고리스·9_중고승용 본문 근거)."""
    cur.execute("INSERT INTO condition_rule VALUES(?,?,?,?,?,?)",
                ("법인", "적용금리",
                 "대표자 입보 시 대표자 신용(금리등급) 기준으로 적용되며, 대표자 미입보 시 개인 금리등급 7등급 금리로 적용됩니다.",
                 "법인 진행 건", EFFECTIVE, LEASE_PDF.name))
    return 1


def extract_fees_and_terms(cur: sqlite3.Cursor) -> int:
    """중고승용 수수료·연체·슬라이딩, 중고리스 금리/IRR, 심사 한도·연식·카히스토리,
    FAQ 수치(특별승인·책임채권·임직원금리) → condition_rule (원문 근거)."""
    S, L = SUSEUNG_PDF.name, LEASE_PDF.name
    FAQ = SOURCE_DIR / "4_오토운영팀 FAQ 가명샘플.xlsx"
    JS = SOURCE_DIR / "7_중고차승용심사운영기준.docx"
    rules = [
        # 중고승용 (9)
        ("중고승용", "연체이자율", "대출금리 17.0% 미만: 약정금리 +3.0% / 대출금리 17.0% 이상: 20.0%", "", S),
        ("중고승용", "중도상환수수료율", "취급금리 ~20% 30.0% 부터 ~30% 40.0% 까지 구간별 1%p 증가", "대출 경과기간 3년 초과 시 면제", S),
        ("중고승용", "슬라이딩", "기준 수수료 內 수수료 1% 차감 시 금리 1% 인하", "", S),
        ("중고승용", "판촉수수료", "대출금액 5백만원 이하 3.00% / 5백만원 초과 2.25% + 37,500원", "VAT 미포함, 24개월 미만 2.0%", S),
        ("중고승용", "네고 상한", "거점장 전결 최대 -2.0%, 증빙(개인) 최대 -1.0% (등급별 상이)", "", S),
        # 중고리스 (8)
        ("중고리스", "금융리스 금리", "고객별 금리등급·리스기간별 차등(1개월 기준 등급1~8 = 21.0%~28.0%)", "금융리스 운영 금리table", L),
        ("중고리스", "IRR NEGO", "심사등급 최대 -20.0%, 지점NEGO(취득원가 9천만↑) -21.0%, 거점장 전결 -20.1%, 본사NEGO(타사 경합) -21.1%, 중복 최대 -2.0%(본사 협의 시 -3.0%)", "", L),
        ("중고리스", "취급기간·주행거리", "금융리스 최초등록일~10년 & 주행 15만km 內 / 운용리스 주행 50만km 內·연 33,444km 초과 불가", "", L),
        # 심사 공통 (6/7)
        ("심사", "신청가능금액", "차량가격 + 제부대비용 이내 (튜닝·개조비용 제외)", "", JS.name),
        ("심사", "최대대출가능금액", "MIN(차량가격 + 부대비용, 중고차 DB시세의 110%)", "", JS.name),
        ("심사", "대상물품 연식", "중고승용/수입승용/25인승 미만 승합/4.5톤 미만 상용: 연식 10년 이내 (10~15년 선별취급, 4.5~5톤 상용 12년 이내)", "특장·특수·영업용 제외", JS.name),
        ("심사", "카히스토리", "전손 차량은 본사승인. 단, 대출신청금액이 차량시세 50% 이내 & 실물확인서 징구 시 시스템 판정으로 취급 가능", "", JS.name),
        # FAQ 수치 (4)
        ("특별승인", "취급기준", "불가: 연체자·규제초과·4억원 초과 / 한도: 직전분기 실적 8%(리스 총한도 30% 내) / 복원 60% / 금리 협의 불가", "", FAQ.name),
        ("책임채권", "한도", "딜러 초기 3억원·승인 시 5억원 이내 증액 / 제휴점 담보금액의 7배수(기본 담보 4천만원 이상)", "", FAQ.name),
        ("임직원", "금리", "기준금리(3년 만기) + 0.7% 운영", "", FAQ.name),
    ]
    cur.executemany("INSERT INTO condition_rule VALUES(?,?,?,?,?,?)",
                    [(p, a, v, c, EFFECTIVE, s) for (p, a, v, c, s) in rules])
    return len(rules)


def build() -> dict:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    _schema(cur)
    n = extract_suseung_naegukin(cur)
    nf = extract_suseung_foreigner(cur)
    seed_condition_rules(cur)
    nt = extract_truck(cur)
    nl = extract_lease_residual_groups(cur)
    nj = extract_jaego(cur)
    npromo = extract_promotion(cur)
    ncorp = extract_corporate(cur)
    nfee = extract_fees_and_terms(cur)
    con.commit()
    con.close()
    return {"rate_grade_rows": n, "foreigner_rows": nf, "truck_conditions": nt,
            "lease_groups": nl, "jaego_rules": nj, "promotion_rules": npromo,
            "corporate_rules": ncorp, "fees_terms": nfee, "db": str(DB_PATH)}


if __name__ == "__main__":
    print(build())
