---
description: 반복형 실행/검증/보완 루프 — Phase 0~4 를 3회 반복하며 스스로 검증·보완
---

# /loop — 3회 반복 오케스트레이션

전체 사이클(Phase 0→4 실행+검증 → 플랜 보완)을 **3회 반복**한다.
실제 구현은 당신(에이전트)이 하고, 진행/검증/보완은 `scripts/orchestrate.py` 가 강제·기록한다.

## 시작
- 최초 1회만: `python scripts/orchestrate.py init --iterations 3`

## 매 스텝 반복 (status 가 done 이 될 때까지)
1. `python scripts/orchestrate.py next` 로 **지금 할 행동**을 확인한다.
2. 안내된 스텝을 수행한다.
   - **implement**: `CLAUDE.md` 불변규칙 준수하며 해당 `phases/phase_<N>*.md` 의 Tasks/Outputs 를 구현.
     완료 후 `execute.py handoff <phase>` → `execute.py complete <phase>` → `orchestrate.py verify <phase>`.
   - **reflect**(검증 실패): `phases/RESULTS/verify/<phase>.json` 의 findings 를 분석해
     **근본 원인**을 찾고 docs/플랜/코드를 보완한다. `orchestrate.py improve --note "..."` 로 기록 후
     재구현 → `orchestrate.py verify <phase>`.
   - **iteration_reflect**(회차의 0~4 통과): 전체를 회고하고 다음 회차 개선점을 도출.
     `orchestrate.py reflect --note "회고+개선계획"`.
3. `next` 가 다시 가리키는 스텝을 계속 수행한다.

## 규칙
- 검증(verify) 없이 단계를 통과시키지 않는다. 검증 실패 시 반드시 보완(improve)하고 재검증한다.
- 보완은 추측이 아니라 findings 근거로 한다. 변경은 `docs/PLAN_CHANGELOG.md` 에 누적된다.
- 3회 반복이 끝나면(status=done) 최종 상태와 PLAN_CHANGELOG 를 요약 보고한다.
- 단계 건너뛰기·범위 이탈 금지(필요 시 docs/ADR.md 기록).

인자: `$ARGUMENTS` (비우면 현재 상태에서 이어서 진행)
