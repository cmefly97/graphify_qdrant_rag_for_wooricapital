#!/usr/bin/env python3
"""
execute.py — Phase 순차 실행 + 상태 관리 + 핸드오프 하네스 러너.

phases/state.json 을 단일 진실원으로 단계 상태를 관리한다.
- 단계는 순서대로만 진행(이전 단계 미완료 시 다음 단계 start 차단).
- 단계 완료(complete)는 다음 두 게이트를 통과해야 한다:
    (1) phase_<N>.md 의 `## Outputs` 에 선언된 산출물 경로가 실제로 존재
    (2) phases/RESULTS/phase_<N>.md 핸드오프 요약 문서가 존재
  → 다음 단계는 이 RESULTS 요약 + 실제 산출물만 보면 이어받을 수 있다.

사용법:
    python scripts/execute.py status                 # 전체 상태 + 현재 단계
    python scripts/execute.py outputs <phase_id>     # 선언된 산출물과 존재여부
    python scripts/execute.py handoff <phase_id>     # RESULTS 요약 템플릿 생성
    python scripts/execute.py start <phase_id>       # 단계 시작(in_progress)
    python scripts/execute.py complete <phase_id>    # 단계 완료(게이트 검증)
    python scripts/execute.py complete <phase_id> --force   # 게이트 무시하고 완료
    python scripts/execute.py reset <phase_id>       # 단계 되돌리기(pending)
    python scripts/execute.py init                   # phases/*.md 스캔해 state.json 동기화
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASES_DIR = ROOT / "phases"
RESULTS_DIR = PHASES_DIR / "RESULTS"
STATE_FILE = PHASES_DIR / "state.json"

PHASE_RE = re.compile(r"^phase_(\d+)_?.*\.md$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_phases() -> list[dict]:
    found = []
    for p in PHASES_DIR.glob("phase_*.md"):
        m = PHASE_RE.match(p.name)
        if not m:
            continue
        found.append({"id": f"phase_{int(m.group(1))}", "num": int(m.group(1)), "file": p.name})
    found.sort(key=lambda x: x["num"])
    return found


def parse_outputs(phase_file: str) -> list[str]:
    """phase md 의 `## Outputs` 섹션에서 백틱 경로들을 추출."""
    text = (PHASES_DIR / phase_file).read_text(encoding="utf-8")
    m = re.search(r"^##\s*Outputs.*?$(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if not m:
        return []
    return re.findall(r"`([^`]+)`", m.group(1))


def results_doc_path(num: int) -> Path:
    return RESULTS_DIR / f"phase_{num}.md"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"current_phase": None, "phases": [], "updated_at": None}


def save_state(state: dict) -> None:
    state["updated_at"] = _now()
    PHASES_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def init_state() -> dict:
    state = load_state()
    existing = {p["id"]: p for p in state.get("phases", [])}
    phases = []
    for ph in discover_phases():
        prev = existing.get(ph["id"], {})
        phases.append(
            {
                "id": ph["id"],
                "num": ph["num"],
                "file": ph["file"],
                "status": prev.get("status", "pending"),
                "started_at": prev.get("started_at"),
                "completed_at": prev.get("completed_at"),
                "artifacts": prev.get("artifacts", []),
                "results_doc": prev.get("results_doc"),
            }
        )
    state["phases"] = phases
    if state.get("current_phase") is None and phases:
        nxt = next((p["id"] for p in phases if p["status"] != "completed"), phases[-1]["id"])
        state["current_phase"] = nxt
    save_state(state)
    return state


def _get(state: dict, phase_id: str) -> dict | None:
    return next((p for p in state["phases"] if p["id"] == phase_id), None)


def cmd_status(state: dict) -> int:
    if not state["phases"]:
        print("등록된 phase 가 없습니다. 'python scripts/execute.py init' 실행하세요.")
        return 1
    icon = {"pending": "○", "in_progress": "◐", "completed": "●"}
    print(f"현재 단계: {state.get('current_phase')}")
    print("-" * 56)
    for p in state["phases"]:
        rd = "✓RESULTS" if results_doc_path(p["num"]).exists() else " "
        print(f" {icon.get(p['status'], '?')} {p['id']:<10} [{p['status']:<11}] {p['file']:<22} {rd}")
    return 0


def cmd_outputs(state: dict, phase_id: str) -> int:
    target = _get(state, phase_id)
    if not target:
        print(f"[ERROR] 알 수 없는 단계: {phase_id}")
        return 1
    declared = parse_outputs(target["file"])
    if not declared:
        print(f"[INFO] {phase_id} 에 선언된 Outputs 가 없습니다.")
        return 0
    print(f"{phase_id} 선언 산출물:")
    for rel in declared:
        mark = "✓" if (ROOT / rel).exists() else "✗(없음)"
        print(f"  {mark} {rel}")
    rd = results_doc_path(target["num"])
    print(f"RESULTS 요약: {'✓' if rd.exists() else '✗(없음)'} phases/RESULTS/{rd.name}")
    return 0


def cmd_handoff(state: dict, phase_id: str) -> int:
    target = _get(state, phase_id)
    if not target:
        print(f"[ERROR] 알 수 없는 단계: {phase_id}")
        return 1
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rd = results_doc_path(target["num"])
    if rd.exists():
        print(f"[INFO] 이미 존재: phases/RESULTS/{rd.name}")
        return 0
    declared = parse_outputs(target["file"])
    bullets = "\n".join(f"- `{p}` — (설명)" for p in declared) or "- (산출물 경로)"
    rd.write_text(
        f"""# RESULTS — {phase_id} 핸드오프 요약

> 다음 단계는 이 문서 + 아래 산출물만 보면 이어받을 수 있어야 한다.

## 무엇을 만들었나 (요약)
- (핵심 결과 2~4줄)

## 산출물 (어디에)
{bullets}

## 다음 단계가 이것을 어떻게 쓰나
- (예: Phase 2 검색엔진이 `data/tables.db` 를 수치 조회에 사용)

## 주의/제약 (이어받는 사람이 알아야 할 것)
- (알려진 한계, 미처리 항목, 가정)

## 검증 근거
- (통과한 테스트/확인 명령)
""",
        encoding="utf-8",
    )
    print(f"[OK] 템플릿 생성: phases/RESULTS/{rd.name}  → 내용을 채운 뒤 complete 하세요.")
    return 0


def cmd_start(state: dict, phase_id: str) -> int:
    target = _get(state, phase_id)
    if not target:
        print(f"[ERROR] 알 수 없는 단계: {phase_id}")
        return 1
    for p in state["phases"]:
        if p["num"] < target["num"] and p["status"] != "completed":
            print(f"[BLOCK] 이전 단계 {p['id']} 가 완료되지 않았습니다(현재 {p['status']}). 순서대로 진행하세요.")
            return 2
    target["status"] = "in_progress"
    target["started_at"] = target.get("started_at") or _now()
    state["current_phase"] = phase_id
    save_state(state)
    print(f"[OK] {phase_id} 시작(in_progress). phases/{target['file']} 의 Tasks 를 진행하세요.")
    return 0


def cmd_complete(state: dict, phase_id: str, force: bool = False) -> int:
    target = _get(state, phase_id)
    if not target:
        print(f"[ERROR] 알 수 없는 단계: {phase_id}")
        return 1
    if target["status"] != "in_progress":
        print(f"[WARN] {phase_id} 가 in_progress 상태가 아닙니다(현재 {target['status']}).")

    # 게이트 1: 선언 산출물 존재 검증
    declared = parse_outputs(target["file"])
    artifacts = [{"path": rel, "exists": (ROOT / rel).exists()} for rel in declared]
    missing = [a["path"] for a in artifacts if not a["exists"]]

    # 게이트 2: RESULTS 핸드오프 요약 존재
    rd = results_doc_path(target["num"])

    problems = []
    if missing:
        problems.append("선언 산출물 누락: " + ", ".join(missing))
    if not rd.exists():
        problems.append(f"RESULTS 요약 없음: phases/RESULTS/{rd.name} (→ 'execute.py handoff {phase_id}')")

    if problems and not force:
        print(f"[BLOCK] {phase_id} 완료 게이트 실패:")
        for pr in problems:
            print(f"  - {pr}")
        print("  (게이트를 무시하려면 --force)")
        return 2

    target["status"] = "completed"
    target["completed_at"] = _now()
    target["artifacts"] = artifacts
    target["results_doc"] = f"phases/RESULTS/{rd.name}" if rd.exists() else None
    nxt = next((p["id"] for p in state["phases"] if p["status"] != "completed"), None)
    state["current_phase"] = nxt
    save_state(state)
    flag = " (--force)" if (problems and force) else ""
    print(f"[OK] {phase_id} 완료(completed){flag}. 산출물 {len(artifacts)}개 기록. 다음 단계: {nxt or '없음(전체 완료)'}")
    return 0


def cmd_reset(state: dict, phase_id: str) -> int:
    target = _get(state, phase_id)
    if not target:
        print(f"[ERROR] 알 수 없는 단계: {phase_id}")
        return 1
    target["status"] = "pending"
    target["started_at"] = None
    target["completed_at"] = None
    target["artifacts"] = []
    target["results_doc"] = None
    state["current_phase"] = phase_id
    save_state(state)
    print(f"[OK] {phase_id} 를 pending 으로 되돌렸습니다.")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "init":
        init_state()
        return cmd_status(load_state())
    state = load_state()
    if not state["phases"]:
        state = init_state()
    if cmd == "status":
        return cmd_status(state)
    if cmd in {"start", "complete", "reset", "outputs", "handoff"}:
        if len(argv) < 3:
            print(f"[ERROR] 사용법: python scripts/execute.py {cmd} <phase_id>")
            return 1
        phase_id = argv[2]
        if cmd == "start":
            return cmd_start(state, phase_id)
        if cmd == "complete":
            return cmd_complete(state, phase_id, force="--force" in argv[3:])
        if cmd == "reset":
            return cmd_reset(state, phase_id)
        if cmd == "outputs":
            return cmd_outputs(state, phase_id)
        if cmd == "handoff":
            return cmd_handoff(state, phase_id)
    print(f"[ERROR] 알 수 없는 명령: {cmd}")
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
