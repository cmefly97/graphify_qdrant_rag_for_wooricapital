# PLAN_CHANGELOG — 반복 보완 이력

오케스트레이션(`/loop`, `scripts/orchestrate.py`) 반복 중 검증 결과에 따라
플랜/문서/코드를 보완한 내역을 시간순으로 누적한다.

- `improve` : 특정 phase 검증 실패를 보완한 기록(근거=verify findings).
- `iteration_reflect` : 한 회차(0~4 전체) 종료 후 회고와 다음 회차 개선계획.

> 이 파일은 `orchestrate.py improve/reflect` 가 자동으로 append 한다. 수동 편집도 가능.

## [2026-06-28T15:32:52.000540+00:00] iter1 · phase_0 · improve
verify.py 의 pytest 실행 환경에서 'No module named app' 발생(루트가 sys.path 에 없음). pyproject.toml [tool.pytest.ini_options] pythonpath=['.'] 추가로 해결. 플랜 보완: Phase0 Outputs 에 pyproject.toml 추가 권고.

## [2026-06-28T15:42:11.876165+00:00] iter1 · ALL · iteration_reflect
iter1 회고: 5개 예시+변형 전부 정확(수치 100%/출처 100%). 잔존 개선점 → (1) 외국인 구간별(12/24/36/48개월) GL표 미추출, (2) 벡터검색이 폴백 임베딩이라 설명형 약함, (3) 골든셋 10문항으로 작음. iter2 개선계획: 외국인 구간 금리표 추출+회귀테스트 추가. iter3: 골든셋 확장 + 근거없음 처리 강화.

## [2026-06-28T15:42:57.707130+00:00] iter2 · phase_1 · improve
iter2 개선 구현: 외국인 구간별(12/24/36/48개월) GL 금리표 추출 추가(pipeline/extract_tables.extract_suseung_foreigner) + 회귀테스트(외국인 등급2·36개월=39.0%). tables.db rate_grade +36행.

## [2026-06-28T15:43:23.179139+00:00] iter2 · ALL · iteration_reflect
iter2 회고: 외국인 구간 금리표 추출 추가로 수치 커버리지 확대(rate_grade 9→45행), 전 phase 검증 통과, eval 100% 유지. iter3 개선계획: (1) 근거 유사도 임계값 미만이면 무관 컨텍스트 대신 '규정에 명시되어 있지 않습니다' 반환(환각/오답 방지 강화), (2) 골든셋에 무관질의·경계질의 추가.

## [2026-06-28T15:45:22.094604+00:00] iter3 · phase_2 · improve
iter3 개선 구현: (1) 무관 질의 처리 강화 — 폴백 임베딩 코사인이 무관/관련 질의 모두 0.3~0.4로 분리 불가함을 발견. 코사인 임계 대신 어휘중첩 게이트(_lexical_relevant)로 교체해 무관 질의는 '규정에 명시되어 있지 않습니다' 반환. (2) 금리 조회 구간(개월) 인식 추가. (3) 골든셋 12문항으로 확장(무관2+외국인구간1). eval 12/12 100%.

## [2026-06-28T15:45:31.616932+00:00] iter3 · ALL · iteration_reflect
iter3 회고: 환각/오답 방지 강화(무관질의 차단), 금리 구간 조회, 골든셋 확장 완료. 전 phase 검증 통과, eval 12/12(100%), 수치 100%, 출처 100%. MVP 목표 충족. 다음(범위 외): 실제 게이트웨이 연결 재인덱싱, 타 상품 표 확장, SSO/로깅/스케줄러 운영전환.

## [iter3+ 유지보수] phase_2 · improve
게이트웨이 응답 파서 보강: Qwen3.6 등 reasoning 모델이 content=null + reasoning_content 에 답을 담는 케이스 대응(_extract_content). 사내망 검증 결과 EMBED(Octen 4096d)/HCX-SEED-32B/Qwen3.6 = 3/3 통과.

## [iter3+ 유지보수] phase_1 · improve
Qdrant 적재 경로 추가(app/qdrant_io.py): QDRANT_URL 접속 시 컬렉션을 실제 임베딩 차원(Cosine)으로 재생성 후 upsert, 미연결 시 로컬 vector_store.json 폴백. retriever 도 Qdrant 우선 검색. 폴백(256d)·실제(4096d) 차원 혼입 방지를 위해 컬렉션은 매 적재 시 실제 벡터 길이로 재생성. 재인덱싱 원스톱 scripts/reindex.py 추가.

## [iter3+ 유지보수] phase_4 · improve
실연결 재인덱싱(실제 Octen 4096d, Qdrant woori_auto 252점 적재) 후 골든셋 neg2가 LLM 경로로 정확히 거절했으나 mode!=none 으로 오답 처리됨(과한 기준). 평가 기준 보강: unknown 항목은 mode=none 또는 답변이 '규정에 명시되어 있지 않습니다'면 정답(환각 회피가 본질). + 임베딩 배치화/진행률, 배치 실패 시 개별 실호출 폴백.

## [확장] phase_1 · improve (타 상품 표 추출)
중형트럭(상품조건 표 20행), 재고금융(대상물품·고객·채권·연체 5행), 중고리스 잔가군(S~V 70행)을 동일 스키마로 추출(extract_truck/extract_lease_residual_groups/extract_jaego). tables.db: rate_grade 45, condition_rule 32, lease_residual_group 70.

## [확장] phase_2 · improve (다상품 조회)
tables_lookup 에 잔가군 조회(lookup_residual_group) + 범용 조건 조회(lookup_condition_generic) 추가. 자가테스트로 발견·수정: (1) lease_residual_group effective_date 컬럼 오류, (2) condition 텍스트 매칭으로 인한 오선택 → condition 점수 제외, (3) 상품 교차 매칭 → 질의 상품명으로 범위 한정 + 상품명 토큰 점수 제외.

## [확장] phase_4 · improve (골든셋 51문항)
골든셋 12→51문항 확대(중고승용 등급1~9·외국인 구간·네고, 중형트럭 6, 재고금융 6, 잔가군 4, 무관 3). 반복 검증으로 2건 오매칭 자가수정 후 51/51 통과(정확도 100%, 수치 100%, 출처 100%).

## [운영전환 phase_5] 2·3·5 구현 (4·1·6 문서화 보류)
(2) 질의 로깅 query_log.db + /feedback + /stats + /dashboard. (3) scheduled_reindex.py: 회귀게이트 통과 시만 PROMOTED + reindex_versions.jsonl 이력. (5) ci_gate.py(임계 게이트) + ab_test.py(베이스라인 A/B). 임계 공용 eval/gate.py. 테스트 tests/test_logging.py·test_ci_ab.py 파일 보존. 전체 pytest 24 passed, ci_gate PASS, A/B 회귀 0. 4(인프라)·1(SSO)·6(보안)은 docs/PRODUCTION_TRANSITION.md 에 상세 문서화 후 보류.

## [확장] phase_3 · improve (서버 서빙 웹 채팅)
Node 빌드 없이 테스트하도록 FastAPI 가 채팅 화면(GET /)·대시보드(/dashboard)를 직접 서빙. 예시칩·답변·출처배지·근거노드·👍/👎 피드백 포함(같은 출처라 CORS 불필요). tests/test_logging.py 에 웹 라우트 테스트 추가. 전체 pytest 25 passed.

## [확장] phase_2·3 · improve (처리과정 트레이스 UI)
질의 파이프라인을 단계별 트레이스로 노출(answer_query with_trace): 라우팅→쿼리확장→테이블조회→벡터검색(소요ms·상위히트)→그래프탐색(노드)→재랭킹→생성. 트레이스 표시 시 벡터·그래프를 항상 수행해 화면에서 확인 가능. 그래프 시드에 질의어-라벨 매칭 추가해 관련 개념 노드 반환. 웹 화면을 좌(채팅)/우(처리과정) 분할. eval/tests 는 with_trace=False 로 기존 속도 유지. 전체 pytest 25 passed.

## [수정] phase_1·2 · improve (프로모션 기준 누락 + 오매칭)
원인: '프로모션 기준'이 9_중고승용 PDF 본문엔 있으나 tables.db 미추출 → 테이블 조회 실패 → 오프라인 폴백 임베딩이 접두어 유사한 무관 FAQ('차량 대금 지급 후 프로세스') 반환.
조치: (1) extract_promotion 추가 — 우량고객 금리(1등급&NICE933&KCB976→G/L 7.6%, 법인 제외)·주말 0.5% 인하·최저금리 5.9%를 condition_rule(product='프로모션')로 추출. (2) lookup_promotion 핸들러 추가. (3) '네고' 조회 핸들러(lookup_nego_overview) 추가 및 범용검색 수식어(내국인/외국인) 제외. (4) 범용 조건검색이 상품명 불일치 시 흔한 단어 1개('주말')로 오매칭하던 문제 → 비범위 질의는 상품명 일치 필수(gate)로 차단. 골든셋 +2(promo·nego), eval 53/53(100%), pytest 27 passed.

## [수정+확장] phase_1·2 · improve (source 전체 누락 항목 반영)
source 전 문서 스캔 후 tables.db 누락/오류 일괄 반영. (1) 정확도 버그: nice_band 를 원문 실제값으로 교체(등급1=933↑,2=884↑,…,8=610↑,9=350↑) — 기존 3개 러프값 폐기. 부작용: NICE 885점은 실제로 2등급 구간(884~932)이라 초기 예시의 'NICE 1등급'은 정정됨(원문 기준). (2) 추출 추가(extract_fees_and_terms): 중고승용(연체이자율·중도상환수수료율·슬라이딩·판촉수수료·네고상한), 중고리스(금융리스 금리·IRR NEGO·취급기간/주행거리), 심사(신청가능금액·최대대출 DB시세110%·대상물품 연식·카히스토리), FAQ(특별승인·책임채권·임직원 금리). (3) lookup_fact 키워드 라우터(속성 우선) 추가, 슬라이딩=엔카/수수료 분리, nego_overview 에 IRR/리스 가드. 골든셋 +12(총 65), eval 65/65(100%), pytest 28 passed.

## [리팩터링] phase_2 · improve (프롬프트/템플릿 모듈 분리)
답변 표현·정책과 프롬프트 지시문을 코드 곳곳에서 분리해 중앙 모듈화(동작 불변, 65/65 유지).
- app/prompts.py: 시스템 프롬프트(상담사 톤·근거만·출처·모르면 모른다), 답변 스타일 4종(mode), NO_EVIDENCE, 컨텍스트 정책(원문1차/구조화보조 원칙, MAX_CONTEXT_CHUNKS·CHARS 캡, MIN_CONTEXT_SCORE 저점수컷), lexical_relevant 게이트, build_messages.
- app/templates.py: 표기 정책 플래그(고객유형 미지정=내국인 / 최저금리 산술 금지 / 개월 포맷), 출처 표기(format_sources·source_badge), 문장 템플릿(rate_answer·nego_overview·promotion_criteria·promotion_judgment·condition_line·context_only).
- generator.py / tables_lookup.py 는 위 모듈을 사용하도록 리팩터링. 정책·문구 변경 시 두 파일만 수정.

## [2026-07-15] manual · config · Qwen 접속정보 추가
Qwen 폴백 LLM 접속 엔드포인트를 명시적으로 추가/수정: `QWEN_BASE_URL=http://223.130.140.218:8000/v1/chat/completions`.
반영 파일: `.env.example`, `app/config.py`(Settings.qwen_base_url 필드 신설), `PROJECT_PLAN.md`(env 블록), `docs/ARCHITECTURE.md`, `docs/ADR.md`. `.env` 는 hook(secret_guard)으로 직접 편집 차단 → 동일 한 줄을 사용자가 수동 반영.
기존에는 QWEN_MODEL 만 존재하고 접속 URL 이 없어 폴백이 HCX30_BASE_URL 을 재사용하는 구조였음.
