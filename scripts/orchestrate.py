#!/usr/bin/env python3
"""
orchestrate.py — 반복형 실행/검증/보완 오케스트레이터.

전체 사이클(Phase 0→4 실행+검증 → 플랜 보완)을 max_iterations(기본 3)회 반복한다.
실제 '구현'은 에이전트(Claude)가 수행하고, 본 스크립트는 다음을 강제·기록하는 드라이버다.
  - 진행 위치(반복회차/단계/스텝)를 phases/orchestration.json 에 저장
  - 단계별 검증(verify.py) 실행 및 결과 기록
  - 검증 실패 시 '보완(reflect)' 스텝으로 전이 → 플랜/문서 수정 유도
  - 보완 내역을 docs/PLAN_CHANGELOG.md 에 누적

상태 흐름(스텝):
  implement → (verify) → 통과 시 다음 phase / 실패 시 reflect → improve → implement(재시도)
  한 회차의 phase 0~4 가 모두 통과하면 → iteration_reflect(회차 플랜 보완) → 다음 회차
  max_iterations 회차 완료 시 → done

명령:
  orchestrate.py init [--iterations N]      # 오케스트레이션 시작(기본 3회)
  orchestrate.py status                     # 현재 위치/이력 요약
  orchestrate.py next                        # 지금 해야 할 행동 안내(에이전트가 따른다)
  orchestrate.py verify [<phase_id>]         # 현재(또는 지정) phase 검증→기록→전이
  orchestrate.py improve --note "..."        # 검증 실패 보완 기록 → implement 재시도
  orchestrate.py reflect --note "..."        # 회차 단위 플랜 보완 → 다음 회차로
  orchestrate.py reset                        # 오케스트레이션 초기화
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from execute import discover_phases  # noqa: E402

ORCH_FILE = ROOT / "phases" / "orchestration.json"
CHANGELOG = ROOT / "docs" / "PLAN_CHANGELOG.md"
VERIFY_PY = SCRIPTS / "verify.py"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _arg(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else default


def load() -> dict | None:
    return json.loads(ORCH_FILE.read_text(encoding="utf-8")) if ORCH_FILE.exists() else None


def save(state: dict) -> None:
    state["updated_at"] = _now()
    ORCH_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def cur_phase(state: dict) -> str | None:
    order = state["phase_order"]
    i = state["phase_index"]
    return order[i] if 0 <= i < len(order) else None


# ---------- 명령 ----------

def cmd_init(argv: list[str]) -> int:
    iters = int(_arg(argv, "--iterations", 3))
    order = [ph["id"] for ph in discover_phases()]
    if not order:
        print("[ERROR] phase 파일이 없습니다. phases/phase_*.md 를 먼저 만드세요.")
        return 1
    state = {
        "max_iterations": iters,
        "iteration": 1,
        "phase_index": 0,
        "phase_order": order,
        "step": "implement",
        "status": "running",
        "history": [],
        "created_at": _now(),
    }
    save(state)
    if not CHANGELOG.exists():
        CHANGELOG.write_text(
            "# PLAN_CHANGELOG — 반복 보완 이력\n\n"
            "오케스트레이션 반복 중 검증 결과에 따라 플랜/문서를 보완한 내역을 누적한다.\n",
            encoding="utf-8",
        )
    print(f"[OK] 오케스트레이션 시작: {iters}회 반복, phases={order}")
    return cmd_status(state)


def cmd_status(state: dict) -> int:
    print(f"상태: {state['status']}  |  회차 {state['iteration']}/{state['max_iterations']}"
          f"  |  단계 {cur_phase(state) or '-'}  |  스텝 {state['step']}")
    hist = state["history"][-6:]
    if hist:
        print("- 최근 이력:")
        for h in hist:
            extra = h.get("passed")
            tag = "" if extra is None else (" PASS" if extra else " FAIL")
            print(f"  · iter{h['iteration']} {h['phase']:<8} {h['event']}{tag} {h.get('note','')[:50]}")
    return 0


def cmd_next(state: dict) -> int:
    if state["status"] == "done":
        print("✅ 모든 반복 완료(done). 더 진행할 작업이 없습니다.")
        return 0
    it, mx = state["iteration"], state["max_iterations"]
    phase = cur_phase(state)
    step = state["step"]
    print(f"[회차 {it}/{mx}] ", end="")
    if step == "implement":
        print(f"▶ {phase} 구현. CLAUDE.md 불변규칙 준수 + phases/{phase}*.md 의 Tasks/Outputs 완수.\n"
              f"   완료 후: python scripts/execute.py handoff {phase}  (RESULTS 작성)\n"
              f"           python scripts/execute.py complete {phase}  (Outputs 게이트)\n"
              f"           python scripts/orchestrate.py verify {phase}  (검증→전이)")
    elif step == "reflect":
        print(f"⚠ {phase} 검증 실패. findings(phases/RESULTS/verify/{phase}.json)를 분석해 원인 파악 →\n"
              f"   플랜/문서(docs/, phases/{phase}*.md) 또는 코드를 보완하라.\n"
              f"   기록: python scripts/orchestrate.py improve --note \"무엇을 왜 어떻게 고쳤는지\"\n"
              f"   그 다음 재구현 → orchestrate.py verify {phase}")
    elif step == "iteration_reflect":
        print(f"🔄 회차 {it} 의 phase 0~4 검증 통과. 전체를 돌아보고 다음 회차 개선점을 도출하라.\n"
              f"   (예: 정확도 낮은 질의 유형, 추출 누락, 프롬프트/재랭킹 개선 등)\n"
              f"   기록: python scripts/orchestrate.py reflect --note \"이번 회차 회고 + 다음 회차 개선계획\"")
    return 0


def cmd_verify(state: dict, argv: list[str]) -> int:
    phase = argv[2] if len(argv) > 2 and not argv[2].startswith("--") else cur_phase(state)
    if phase != cur_phase(state):
        print(f"[WARN] 현재 단계는 {cur_phase(state)} 입니다. 요청 단계: {phase}")
    proc = subprocess.run(
        [sys.executable, str(VERIFY_PY), phase, str(state["iteration"])],
        capture_output=True, text=True,
    )
    sys.stderr.write(proc.stderr)
    try:
        report = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        print("[ERROR] verify.py 출력 파싱 실패")
        return 1
    passed = report["passed"]
    state["history"].append({
        "ts": _now(), "iteration": state["iteration"], "phase": phase,
        "event": "verify", "passed": passed, "findings": report["findings"],
    })
    if passed:
        # 다음 phase 로 전진
        state["phase_index"] += 1
        if state["phase_index"] >= len(state["phase_order"]):
            state["step"] = "iteration_reflect"
        else:
            state["step"] = "implement"
        print(f"[OK] {phase} 검증 PASS → 다음: {('회차 회고' if state['step']=='iteration_reflect' else cur_phase(state))}")
    else:
        state["step"] = "reflect"
        print(f"[FAIL] {phase} 검증 실패 → reflect 스텝. findings: {report['findings']}")
    save(state)
    return 0 if passed else 1


def _append_changelog(iteration: int, phase: str, kind: str, note: str) -> None:
    with CHANGELOG.open("a", encoding="utf-8") as f:
        f.write(f"\n## [{_now()}] iter{iteration} · {phase} · {kind}\n{note}\n")


def cmd_improve(state: dict, argv: list[str]) -> int:
    note = _arg(argv, "--note", "")
    if not note:
        print("[ERROR] --note \"보완 내용\" 이 필요합니다.")
        return 1
    phase = cur_phase(state)
    _append_changelog(state["iteration"], phase, "improve", note)
    state["history"].append({
        "ts": _now(), "iteration": state["iteration"], "phase": phase,
        "event": "improve", "note": note,
    })
    state["step"] = "implement"  # 보완 후 재구현 → 재검증
    save(state)
    print(f"[OK] 보완 기록(PLAN_CHANGELOG). {phase} 재구현 후 'orchestrate.py verify {phase}' 하세요.")
    return 0


def cmd_reflect(state: dict, argv: list[str]) -> int:
    if state["step"] != "iteration_reflect":
        print(f"[WARN] 현재 스텝이 iteration_reflect 가 아닙니다(현재 {state['step']}).")
    note = _arg(argv, "--note", "")
    if not note:
        print("[ERROR] --note \"회차 회고/개선계획\" 이 필요합니다.")
        return 1
    _append_changelog(state["iteration"], "ALL", "iteration_reflect", note)
    state["history"].append({
        "ts": _now(), "iteration": state["iteration"], "phase": "ALL",
        "event": "iteration_reflect", "note": note,
    })
    if state["iteration"] >= state["max_iterations"]:
        state["status"] = "done"
        save(state)
        print(f"[OK] 회차 {state['iteration']} 회고 완료. ✅ 전체 {state['max_iterations']}회 반복 종료(done).")
        return 0
    state["iteration"] += 1
    state["phase_index"] = 0
    state["step"] = "implement"
    save(state)
    print(f"[OK] 회차 회고 완료 → 회차 {state['iteration']} 시작(phase_0 부터).")
    return 0


def cmd_reset() -> int:
    if ORCH_FILE.exists():
        ORCH_FILE.unlink()
    print("[OK] orchestration.json 삭제. 'init' 으로 다시 시작하세요.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "init":
        return cmd_init(argv)
    if cmd == "reset":
        return cmd_reset()
    state = load()
    if state is None:
        print("[ERROR] 오케스트레이션 미초기화. 'python scripts/orchestrate.py init' 먼저 실행하세요.")
        return 1
    if cmd == "status":
        return cmd_status(state)
    if cmd == "next":
        return cmd_next(state)
    if cmd == "verify":
        return cmd_verify(state, argv)
    if cmd == "improve":
        return cmd_improve(state, argv)
    if cmd == "reflect":
        return cmd_reflect(state, argv)
    print(f"[ERROR] 알 수 없는 명령: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
