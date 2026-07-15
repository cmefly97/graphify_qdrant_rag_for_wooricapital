#!/usr/bin/env python3
"""
secret_guard.py — PreToolUse hook.

Edit/Write 직전에 호출되어, .env 파일을 직접 덮어쓰려 하거나
변경 내용에 API 키/시크릿이 하드코딩되면 작업을 차단한다.

Claude Code hook 규약:
- stdin 으로 JSON({tool_name, tool_input, ...}) 수신.
- exit code 2 → 작업 차단(블로킹). stderr 메시지가 모델에 전달됨.
- exit code 0 → 통과.
"""
from __future__ import annotations

import json
import re
import sys

# 시크릿으로 의심되는 패턴
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),                 # API key 형태
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]{12,}['\"]"),
]
ALLOW_PLACEHOLDERS = {"********", "<api_key>", "your-key", "changeme", "${", "os.environ", "getenv"}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # 입력 파싱 실패 시 통과(hook 자체가 작업을 막지 않도록)

    tool_input = payload.get("tool_input", {}) or {}
    file_path = str(tool_input.get("file_path", ""))
    content = tool_input.get("content") or tool_input.get("new_string") or ""

    # 1) .env 직접 편집 차단 (.env.example 은 허용)
    if file_path.endswith(".env") and not file_path.endswith(".env.example"):
        print("[secret_guard] .env 파일은 직접 편집하지 않습니다. .env.example 을 수정하세요.", file=sys.stderr)
        return 2

    # 2) 시크릿 하드코딩 차단
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(content):
            snippet = m.group(0)
            if any(ph in snippet for ph in ALLOW_PLACEHOLDERS):
                continue
            print(
                f"[secret_guard] 시크릿으로 의심되는 값이 감지되었습니다: '{snippet[:12]}...'. "
                "키는 .env 로 분리하고 os.environ 으로 읽으세요.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
