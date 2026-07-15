#!/usr/bin/env bash
# 웹 채팅/대시보드 서버 실행 (포트 8010)
# 사용: bash scripts/serve.sh   (또는 PORT=9000 bash scripts/serve.sh)
set -e
cd "$(dirname "$0")/.."
PORT="${PORT:-8010}"
# venv 파이썬을 우선 사용(콘솔 스크립트 셔뱅에 의존하지 않음). 없으면 시스템 python.
PY="${PYTHON:-python3}"
[ -x .venv/bin/python ] && PY=".venv/bin/python"
echo "▶ http://localhost:${PORT}/  (채팅)   http://localhost:${PORT}/dashboard  (대시보드)"
exec "$PY" -m uvicorn app.main:app --reload --port "${PORT}"
