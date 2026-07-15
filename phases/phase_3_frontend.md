# Phase 3 — 프론트엔드 (Frontend)

## 목표
상담사용 채팅 UI를 완성한다(UI_GUIDE 기준).

## Tasks
- [ ] Next.js + React 채팅 화면, SSE 스트리밍 연동
- [ ] 예시 질문 칩(5종)
- [ ] 답변 카드 + 근거 출처 배지(문서·유효일자) + 원문 청크 펼침
- [ ] 수치 답변 표 렌더링(금리등급/GL/네고)
- [ ] 근거 그래프 패널(Cytoscape.js): 시작노드 강조, 관계 라벨, 노드→청크 점프
- [ ] 로딩 단계 표시 + 👍/👎 피드백(로그 자리)

## Outputs (산출물 — complete 시 존재 검증)
- `web/package.json`
- `web/app/page.tsx`
- `web/components/Chat.tsx`
- `web/components/SourceBadge.tsx`
- `web/components/EvidenceGraph.tsx`

## Exit Criteria
- 예시 질문 클릭→답변→출처/그래프 표시 전 흐름 동작.
- 수치 답변이 표로 구조화 표시.
- 반응형·기본 접근성 확인.
