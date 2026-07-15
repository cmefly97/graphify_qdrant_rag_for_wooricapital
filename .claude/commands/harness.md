---
description: 하네스 원스톱 실행 — 헌법/문서/현재 단계를 로드하고 다음 작업을 안전하게 진행
---

# /harness — 단계 실행 원스톱

당신은 이 프로젝트의 하네스 운영자다. 아래 절차를 **순서대로** 따른다.

## 1. 컨텍스트 로드 (항상 먼저)
- `CLAUDE.md`(헌법) 전체를 읽는다. 불변 규칙을 위반하지 않는다.
- `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`를 읽는다.
- `python scripts/execute.py status` 로 현재 단계와 상태를 확인한다.

## 2. 현재 단계 파악
- `phases/state.json`에서 `current_phase`를 확인.
- 해당 `phases/phase_<N>_*.md`를 읽고 **목표 / 작업항목(Tasks) / 완료기준(Exit Criteria)**을 파악한다.

## 3. 실행
- `python scripts/execute.py start <phase_id>` 로 단계를 in_progress로 표시.
- phase 파일의 Tasks를 위에서부터 구현한다. 각 변경마다 hook 검증이 돈다(실패 시 수정 후 재시도).
- 단위테스트를 작성/통과시킨다.

## 4. 완료 판정
- phase 파일의 **Exit Criteria를 모두 충족**했는지 점검한다.
- 충족 시 `python scripts/execute.py complete <phase_id>`.
- 미충족 항목이 있으면 단계를 완료 처리하지 말고 남은 작업을 계속한다.

## 규칙
- 절대 단계를 건너뛰거나 Exit Criteria 미충족 상태로 완료 처리하지 않는다.
- 범위 밖 기능 추가 금지(필요 시 `docs/ADR.md`에 결정 기록 후 진행).
- 수치 환각 금지·출처 의무·게이트웨이 전용 등 CLAUDE.md 불변 규칙 우선.

인자: `$ARGUMENTS` (예: 특정 phase_id 또는 비움 → 현재 단계 진행)
