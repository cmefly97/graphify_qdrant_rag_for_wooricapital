# RESULTS — phase_3 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- Next.js 채팅 UI: 예시 질문 칩, 질의 입력, 답변 카드(라우팅/모드/신뢰도), 출처 배지, 근거 그래프 패널.
- `POST /ask` 백엔드 연동. evidence_nodes 를 Cytoscape 로 시각화.

## 산출물 (어디에)
- `web/package.json` — Next.js + react + cytoscape 의존성.
- `web/app/page.tsx` — 메인 페이지 + 예시 질문 칩 5종.
- `web/components/Chat.tsx` — 채팅·API 호출·답변 렌더.
- `web/components/SourceBadge.tsx` — 출처(문서·유효일자) 배지.
- `web/components/EvidenceGraph.tsx` — 근거 그래프(Cytoscape) 패널.

## 다음 단계가 이것을 어떻게 쓰나
- Phase 4 평가는 동일 `answer_query`/`/ask` 결과를 골든셋으로 채점.

## 주의/제약
- 샌드박스에 Node/npm 런타임이 없어 UI 런타임 빌드는 미실행(파일 구조·로직 검증만).
- API_URL 은 NEXT_PUBLIC_API_URL 환경변수로 주입.

## 검증 근거
- `verify.py phase_3` → outputs_exist ✓ (5개), 전체 pytest ✓.
