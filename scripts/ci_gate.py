#!/usr/bin/env python3
"""CI 회귀 게이트 (운영 전환 항목 5).

pytest + 골든셋 평가를 실행하고 임계(eval/gate.py) 미달이면 비정상 종료(1).
CI 파이프라인·배포 전 점검·스케줄러 게이트와 동일 기준을 공유한다.

사용: python scripts/ci_gate.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from eval.gate import regression_gate
    from eval.run_eval import evaluate, write_report

    # 1) 단위/통합 테스트
    pt = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")],
                        capture_output=True, text=True)
    print(pt.stdout[-600:])
    if pt.returncode != 0:
        print("[ci_gate] FAIL: pytest 실패", file=sys.stderr)
        print(pt.stderr[-600:], file=sys.stderr)
        return 1

    # 2) 골든셋 회귀 게이트
    m = evaluate()
    write_report(m)
    passed, fails = regression_gate(m)
    print(f"[ci_gate] eval accuracy={m['accuracy']} numeric={m['numeric_accuracy']} source={m['source_rate']}")
    if not passed:
        print(f"[ci_gate] FAIL: 회귀 게이트 위반 {fails}", file=sys.stderr)
        return 1
    print("[ci_gate] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
