# Graph Report - ./souce  (2026-06-28)

## Corpus Check
- Corpus is ~4,872 words - fits in a single context window. You may not need a graph.

## Summary
- 57 nodes · 66 edges · 9 communities
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.84)
- Token cost: 110,000 input · 6,567 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]

## God Nodes (most connected - your core abstractions)
1. `중고승용 상품 운영조건 ('26.03.01)` - 9 edges
2. `중고리스 상품운영기준 ('26.03)` - 9 edges
3. `중형트럭 시범운영 세부 운영기준 ('26.01~)` - 7 edges
4. `중고차 재고금융` - 6 edges
5. `재고금융/운영자금 심사운영기준 (E09012)` - 5 edges
6. `오토운영팀 온톨로지 및 에이전트 설계 요청` - 5 edges
7. `운영기준 데이터 (월별 금리·운영 기준)` - 4 edges
8. `금리등급 / G/L 금리 / 조정금리(NEGO)` - 4 edges
9. `중고차 운영자금` - 3 edges
10. `GRAS 등급 판정 (안티프로드)` - 3 edges

## Surprising Connections (you probably didn't know these)
- `사업자 업력 1년 이상 기준` --semantically_similar_to--> `대상고객 (개인사업자/법인)`  [INFERRED] [semantically similar]
  10_샘플_중형트럭 시범운영기준.pdf → 5_재고금융_운영자금심사운영기준.md
- `GRAS 등급 판정 (안티프로드)` --semantically_similar_to--> `R판정/B판정 필터링 (취급가부)`  [INFERRED] [semantically similar]
  5_재고금융_운영자금심사운영기준.md → 9_샘플_중고승용 상품운영기준.pdf
- `NICE CB점수 구간 (등급별 취급기준)` --semantically_similar_to--> `NICE 등급·점수 기준표`  [INFERRED] [semantically similar]
  5_재고금융_운영자금심사운영기준.md → 9_샘플_중고승용 상품운영기준.pdf
- `카히스토리 사전관리 기준` --semantically_similar_to--> `카히스토리 차량 취급기준 (특수사고 불가)`  [INFERRED] [semantically similar]
  5_재고금융_운영자금심사운영기준.md → 9_샘플_중고승용 상품운영기준.pdf
- `운영기준 데이터 (월별 금리·운영 기준)` --references--> `중형트럭 시범운영 세부 운영기준 ('26.01~)`  [INFERRED]
  오토운영팀 온톨로지 및 에이전트.md → 10_샘플_중형트럭 시범운영기준.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **오토운영팀 3대 데이터 출처 (FAQ·규정·운영기준)** — souce_ontology_faq_data, souce_ontology_gyujeong_data, souce_ontology_unyeonggijun_data, souce_ontology_chatbot [EXTRACTED 1.00]
- **신용등급 기반 취급가부 판정 패턴 (NICE/CB/R판정/금리등급)** — souce_5_nice_cb_jeomsu, souce_9_nice_deunggeup_table, souce_9_r_pandan_filtering, souce_9_geumli_deunggeup_gl [INFERRED 0.75]
- **차량 이력·상태 점검 취급기준 (카히스토리·성능점검)** — souce_5_carhistory_jeoghoeb, souce_9_carhistory_chayang_gijun, souce_8_seongneung_jeomgeom [INFERRED 0.75]

## Communities (9 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.24
Nodes (10): 보험가입사실확인서·질권설정 (여전법 35조), 중고리스 취급제한 차종, 금소법 견적서 제공 규정 (직원 한정), 금융리스, IRR Nego 기준 (지점/본사 NEGO), 잔가율표 / 잔가군표 (국산·수입), 중고리스 상품운영기준 ('26.03), 오토리스 심사운영기준 (중고차 심사지침) (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.25
Nodes (8): 취급톤수 조건 (2~10톤 화물차), 사업자 업력 1년 이상 기준, 금리네고 부정사용 페널티, 주행거리 제한 (90만Km 초과 LTV 50%), 중고차기획팀, 중형트럭 시범운영 세부 운영기준 ('26.01~), 대상고객 (개인사업자/법인), 중고차 운영자금

### Community 2 - "Community 2"
Cohesion: 0.25
Nodes (8): 카히스토리 사전관리 기준, 채권서류 징구기준, 차량설정 기준 (1순위 100만원), 대상물품 (취급 대상 차량), 중고차 재고금융, 성능상태점검기록부 확인기준, 카히스토리 차량 취급기준 (특수사고 불가), 엔카 무수수료 (엔카_Zero) 상품

### Community 3 - "Community 3"
Cohesion: 0.29
Nodes (8): Dual Offer 상품 (Dual_C / Dual_O), ESM·딜러 구입대출, 공공마이데이터 (업력/재직 증빙), 중고승용차 할부 구입대출, 중도상환수수료율 / 연체이자율, 중고승용 상품 운영조건 ('26.03.01), 신용구제 상품 운영기준 (SP_R), 슬라이딩 (수수료 차감 금리 인하)

### Community 4 - "Community 4"
Cohesion: 0.40
Nodes (5): Anti-Fraud 운영지침, 취급불가·제한 대상자, GRAS 등급 판정 (안티프로드), JABIS (심사 전산 시스템), R판정/B판정 필터링 (취급가부)

### Community 5 - "Community 5"
Cohesion: 0.40
Nodes (5): 재고금융/운영자금 심사운영기준 (E09012), 삼자약정 (당사·수입상·딜러), 신용관리팀 (소관부서), 수입차 재고금융, 규정 데이터 (핵심 내부 규정)

### Community 6 - "Community 6"
Cohesion: 0.40
Nodes (5): NICE CB점수 구간 (등급별 취급기준), 금리등급 / G/L 금리 / 조정금리(NEGO), 중고승용차 구입대출 (론), HJ Seg. (저주행 우량차 판정), NICE 등급·점수 기준표

### Community 7 - "Community 7"
Cohesion: 0.50
Nodes (5): 오토운영팀 챗봇 (벡터DB 기존 시스템), FAQ 데이터 (지점 일반 문의), 온톨로지·에이전트 전환 (개선 방향), 오토운영팀 온톨로지 및 에이전트 설계 요청, 운영기준 데이터 (월별 금리·운영 기준)

### Community 8 - "Community 8"
Cohesion: 0.67
Nodes (3): 대출금액별 전결기준 (여신직무전결규칙), 평가한도 (판매대수/매출규모 기반), 여신직무전결규칙

## Knowledge Gaps
- **18 isolated node(s):** `신용관리팀 (소관부서)`, `대상물품 (취급 대상 차량)`, `채권서류 징구기준`, `JABIS (심사 전산 시스템)`, `평가한도 (판매대수/매출규모 기반)` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `중고승용 상품 운영조건 ('26.03.01)` connect `Community 3` to `Community 1`, `Community 2`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.349) - this node is a cross-community bridge._
- **Why does `운영기준 데이터 (월별 금리·운영 기준)` connect `Community 7` to `Community 0`, `Community 1`, `Community 3`?**
  _High betweenness centrality (0.292) - this node is a cross-community bridge._
- **Why does `중고리스 상품운영기준 ('26.03)` connect `Community 0` to `Community 2`, `Community 7`?**
  _High betweenness centrality (0.264) - this node is a cross-community bridge._
- **What connects `신용관리팀 (소관부서)`, `대상물품 (취급 대상 차량)`, `채권서류 징구기준` to the rest of the system?**
  _20 weakly-connected nodes found - possible documentation gaps or missing edges._