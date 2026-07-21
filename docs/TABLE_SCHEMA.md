# TABLE_SCHEMA — 운영기준 구조화 테이블 스키마 (tables.db)

> 목적: 금리·등급·네고 등 **정밀 수치를 환각 없이** 조회하기 위한 정규화 스키마.
> 근거 샘플: `souce/9_샘플_중고승용 상품운영기준.pdf` p.1 (내국인/외국인 금리표).
> 본 스키마로 예시 질의 "NICE 885·금리등급 2등급 최저금리"를 **정확히 재현 검증 완료**.

---

## 1. 원천 표 구조 (관찰된 실제 형태)
중고승용 금리표는 **내국인 / 외국인 표가 분리**되어 있고, 다음 특성을 가진다.
- 행: 금리등급 1~9
- 열: `G/L 금리`(내국인 단일 / 외국인은 12·24·36·48개월 구간별), `NEGO 조정금리`(내국인기준, 거점장, 증빙, HJ; 외국인은 대상 NICE구간별)
- **병합 셀 존재**: 증빙·HJ 네고율이 여러 등급에 걸쳐 세로 병합 → 단순 파싱 시 빈칸. **세로 forward-fill 필요**(거점장은 등급별 개별값이므로 무조건 fill 금지).

표 형태가 상품(중고리스/중고승용/중형트럭/재고금융)마다 다르므로, 스키마는 **정규화(long format)** 로 통일해 모든 상품을 수용한다.

---

## 2. 핵심 테이블

### 2.1 `rate_grade` — 금리등급별 G/L 금리
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | INTEGER PK | |
| product | TEXT | 상품 (예: 중고승용 론/할부, 중고리스, 중형트럭) |
| customer_type | TEXT | 내국인 / 외국인 |
| grade | INTEGER | 금리등급 1~9 |
| term_min_months | INTEGER | 구간 시작 개월 (12/24/36/48). 단일이면 12 |
| gl_rate | REAL | G/L 금리(%) |
| effective_date | TEXT | 유효일자 (예: 2026-03-01) |
| source_file | TEXT | 원본 파일명 |
| source_page | INTEGER | 페이지 |
| source_table | TEXT | 표 식별자 |

### 2.2 `nego_rule` — NEGO 조정금리 (네고 권한/조건별)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | INTEGER PK | |
| product | TEXT | 상품 |
| customer_type | TEXT | 내국인 / 외국인 |
| grade_from | INTEGER | 적용 등급 시작 |
| grade_to | INTEGER | 적용 등급 끝 (병합 범위 표현) |
| authority | TEXT | 네고 주체: internal(기준) / 거점장 / 증빙 / HJ / 외국인대상 |
| nice_condition | TEXT | NICE 조건 (예: N1, NICE 1~3, "1%(N1)") |
| nego_rate | REAL | 네고율(%) (불가면 NULL) |
| nego_note | TEXT | 원문 그대로의 조건 텍스트(예: "Nego 불가","3%(N1 or 심사<금리)") |
| effective_date, source_file, source_page, source_table | | rate_grade 동일 |

### 2.3 `condition_rule` — 취급 가부·조건 규칙 (수치형 일반)
취급 개월수, Dual 등급 상한, 엔카 슬라이딩 조건, R/B판정 등 "조회형 규칙"을 키-값+조건으로 보관.
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | INTEGER PK | |
| product | TEXT | 상품/판정명 (예: 론/할부, Dual_C, 엔카 슬라이딩, 신용구제) |
| attribute | TEXT | 속성 (예: 취급개월수, 금리등급상한_내국인, 판정값_R) |
| value | TEXT | 값 (예: "12~72개월", "7", "필터링 취급 불가") |
| condition | TEXT | 부가조건 (예: "19년식 이내 & 주행 연평균500만km 이하") |
| effective_date, source_file, source_page | | |

---

## 3. 조회 패턴 (질의 → SQL)
- "론/할부 취급 개월수?" → `condition_rule WHERE product LIKE '%론/할부%' AND attribute='취급개월수'` → `12~72개월`
- "NICE 885·금리등급 2 최저금리?" →
  `rate_grade WHERE product LIKE '%론/할부%' AND customer_type='내국인' AND grade=2 ORDER BY term_min_months LIMIT 1` (→ 21.0%)
  + `nego_rule WHERE grade_from<=2 AND grade_to>=2 AND customer_type='내국인'` (→ internal 1%(N1), 거점장 11.0, 증빙 15.0, HJ 18.0)
- "듀얼상품 금리등급 몇등급까지?" → `condition_rule WHERE product IN ('Dual_C','Dual_O') AND attribute LIKE '금리등급상한%'`

> **NICE 점수 → 등급** 변환표는 별도 `nice_band(score_min, score_max, nice_grade)` 테이블(원문 실제값, §7 참조). 예: 885점 → 2등급(884~932 구간).

---

## 4. 추출 전략 (병합 셀·표 다양성 대응)
순수 규칙 파싱은 병합 셀·표 변형에 취약하므로 **2단계 하이브리드 추출**을 채택한다.

1. **결정적 추출(pdfplumber)**: `extract_tables()`로 셀 격자 확보. 세로 병합 컬럼(증빙·HJ 등)은 forward-fill, 등급별 개별 컬럼(거점장)은 fill 금지. → 1차 표.
2. **LLM 보정(HCX-30B / hcx-agent-06)**: 1차 표 텍스트 + 본 스키마(JSON 출력 강제)를 주고, 헤더 해석·병합 범위(grade_from/to)·NICE 조건 파싱을 정규화. 출력은 위 테이블 행 JSON.
3. **검증 게이트**: LLM 출력 값이 원본 셀에 실제로 존재하는지 대조(숫자 set 비교). 불일치 시 적재 거부 + 사람 검수 플래그. → **환각 차단**.

> 본 문서의 §1 PoC에서 1번(forward-fill)만으로 예시 답변(21.0/1%/11.0/15.0/18.0)이 정확 재현됨을 확인했다. LLM 보정은 외국인 구간표·타 상품 표의 일반화를 위해 추가한다.

---

## 5. 유효일자·버전 관리
- 운영기준은 월별 갱신 → 모든 행에 `effective_date` 필수. 조회 시 **질의 시점 이하의 최신본** 우선.
- 재인덱싱 시 기존 일자 행은 보존(이력), 신규 일자 행 추가. 충돌 시 최신 우선 + 과거 존재 표기.

---

## 6. 다음 작업 (Phase 1 연계)
- 외국인 구간별 G/L표(12/24/36/48개월) 추출 규칙 추가.
- 중고리스/중형트럭/재고금융 PDF의 표를 동일 스키마로 매핑(상품별 어댑터).
- `nice_band` 변환표 채우기.
- 추출 → 검증 게이트 → tables.db 적재 스크립트화(`pipeline/extract_tables.py`).

---

## 7. 현행화 (2026-06-29) — 실제 적재 커버리지
- **nice_band(수정)**: 원문 실제값. 등급1=933↑, 2=884↑, 3=846↑, 4=812↑, 5=769↑, 6=709↑, 7=669↑, 8=610↑, 9=350↑.
- **rate_grade(45)**: 중고승용 내국인(등급1~9) + 외국인(등급×12/24/36/48개월).
- **nego_rule(36)**: 내국인 등급별 internal/거점장/증빙/HJ.
- **lease_residual_group(70)**: 중고리스 잔가군 S~V ↔ 제조사·차종.
- **condition_rule(51)**: 상품별 조건·수치. product 예 — 론/할부, Dual_C/O, 엔카 슬라이딩, 신용구제, 재고금융, 중형트럭, 프로모션, 법인, 중고승용(연체·중도상환·슬라이딩·판촉·네고상한), 중고리스(금융리스금리·IRR·취급기간), 심사(신청가능·최대대출·대상물품연식·카히스토리), 특별승인·책임채권·임직원.
- 재현: `python -m pipeline.extract_tables` (게이트웨이 불필요).
