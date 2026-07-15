#!/usr/bin/env python3
"""
post_edit_validate.py — PostToolUse hook.

Edit/Write 직후 호출되어, 방금 수정된 파일을 가볍게 검증한다.
- .py  : 구문 컴파일(py_compile) + (가능하면) ruff 체크
- .json: JSON 파싱
- .md   : 기본 통과(존재 확인)

블로킹은 .py 구문 오류와 .json 파싱 오류만(exit 2). 그 외 경고는 stdout.
"""
from __future__ import annotations

import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0
    p = Path(file_path)
    if not p.exists():
        return 0

    suffix = p.suffix.lower()

    if suffix == ".py":
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"[validate] Python 구문 오류: {e}", file=sys.stderr)
            return 2
        # ruff 가 있으면 추가 검사(경고만)
        if shutil.which("ruff"):
            r = subprocess.run(["ruff", "check", str(p)], capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[validate] ruff 경고:\n{r.stdout}{r.stderr}")
        print(f"[validate] OK: {p.name} 구문 정상")
        return 0

    if suffix == ".json":
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[validate] JSON 파싱 오류({p.name}): {e}", file=sys.stderr)
            return 2
        print(f"[validate] OK: {p.name} JSON 정상")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
