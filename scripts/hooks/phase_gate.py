#!/usr/bin/env python3
"""
phase_gate.py — Stop hook (응답 종료 시점).

현재 in_progress 단계의 상태를 점검해 안내한다.
- 테스트 디렉터리가 있으면 pytest 를 빠르게 실행(실패 시 경고).
- 이 hook 은 정보 제공/경고용이며 작업을 강제 차단하지 않는다(exit 0).
  (단계 완료 판정은 execute.py complete + phase 파일 Exit Criteria 로 한다.)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = ROOT / "phases" / "state.json"
TESTS_DIR = ROOT / "tests"


def main() -> int:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            cur = state.get("current_phase")
            ph = next((p for p in state.get("phases", []) if p["id"] == cur), None)
            if ph and ph.get("status") == "in_progress":
                print(f"[phase_gate] 현재 단계 {cur} 진행 중. "
                      f"phases/{ph['file']} 의 Exit Criteria 충족 후 'execute.py complete {cur}' 하세요.")
        except Exception:
            pass

    # 테스트가 있으면 가볍게 실행(경고만)
    if TESTS_DIR.exists() and shutil.which("pytest"):
        r = subprocess.run(["pytest", "-q", str(TESTS_DIR)], capture_output=True, text=True)
        if r.returncode != 0:
            tail = (r.stdout + r.stderr)[-1200:]
            print(f"[phase_gate] ⚠ 테스트 실패/오류 감지:\n{tail}")
        else:
            print("[phase_gate] 테스트 통과")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
