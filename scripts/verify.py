#!/usr/bin/env python3
"""
verify.py — 단계 검증기.

한 phase 의 성공 여부를 다음 체크로 판정한다(블로킹 체크가 모두 통과해야 PASS).
  1. outputs_exist : phase_<N>.md 의 `## Outputs` 경로 존재 (블로킹)
  2. pytest        : 해당 phase 산출물 테스트 또는 tests/ 실행 (블로킹, 미설치/없음 시 skip)
  3. ruff          : 정적 분석 (비블로킹)
  4. custom        : scripts/checks/<phase_id>_check.py 의 check(ROOT) -> list[dict] (있으면)

출력:
  - stdout : 리포트 JSON 1줄 (오케스트레이터가 파싱)
  - stderr : 사람용 요약
  - 파일   : phases/RESULTS/verify/<phase_id>.json
  - exit   : 0=PASS, 1=FAIL, 2=사용법 오류
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from execute import discover_phases, parse_outputs  # noqa: E402

CHECKS_DIR = ROOT / "scripts" / "checks"
VERIFY_OUT = ROOT / "phases" / "RESULTS" / "verify"


def _phase_file(phase_id: str) -> str | None:
    return next((ph["file"] for ph in discover_phases() if ph["id"] == phase_id), None)


def _check_outputs(declared: list[str]) -> dict:
    missing = [p for p in declared if not (ROOT / p).exists()]
    return {
        "name": "outputs_exist",
        "ok": not missing,
        "detail": ("누락: " + ", ".join(missing)) if missing else f"선언 산출물 {len(declared)}개 모두 존재",
        "blocking": True,
    }


def _check_pytest(declared: list[str]) -> dict:
    if not shutil.which("pytest"):
        return {"name": "pytest", "ok": True, "detail": "pytest 미설치 — 건너뜀", "blocking": False}
    test_paths = [p for p in declared if "test" in p and (ROOT / p).exists()]
    if not test_paths and (ROOT / "tests").exists():
        test_paths = ["tests"]
    if not test_paths:
        return {"name": "pytest", "ok": True, "detail": "테스트 파일 없음 — 건너뜀", "blocking": False}
    r = subprocess.run(
        ["pytest", "-q", *[str(ROOT / t) for t in test_paths]],
        capture_output=True, text=True,
    )
    return {"name": "pytest", "ok": r.returncode == 0, "detail": (r.stdout + r.stderr)[-900:].strip(), "blocking": True}


def _check_ruff() -> dict | None:
    if not shutil.which("ruff"):
        return None
    targets = [d for d in ("app", "pipeline", "scripts") if (ROOT / d).exists()]
    if not targets:
        return None
    r = subprocess.run(["ruff", "check", *[str(ROOT / t) for t in targets]], capture_output=True, text=True)
    return {"name": "ruff", "ok": r.returncode == 0, "detail": (r.stdout[-500:] or "ok").strip(), "blocking": False}


def _run_custom(phase_id: str) -> list[dict]:
    f = CHECKS_DIR / f"{phase_id}_check.py"
    if not f.exists():
        return []
    try:
        spec = importlib.util.spec_from_file_location(f"{phase_id}_check", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        if not hasattr(mod, "check"):
            return []
        out = mod.check(ROOT)
        return out if isinstance(out, list) else []
    except Exception as e:  # noqa: BLE001
        return [{"name": f"{phase_id}_custom", "ok": False, "detail": f"커스텀 체크 예외: {e}", "blocking": True}]


def verify(phase_id: str, iteration: int = 0) -> dict:
    pf = _phase_file(phase_id)
    declared = parse_outputs(pf) if pf else []
    checks: list[dict] = [_check_outputs(declared), _check_pytest(declared)]
    ruff = _check_ruff()
    if ruff:
        checks.append(ruff)
    checks.extend(_run_custom(phase_id))

    passed = all(c["ok"] for c in checks if c.get("blocking", True))
    findings = [f"{c['name']}: {c['detail']}" for c in checks if not c["ok"]]
    report = {
        "phase": phase_id,
        "iteration": iteration,
        "passed": passed,
        "checks": checks,
        "findings": findings,
    }
    VERIFY_OUT.mkdir(parents=True, exist_ok=True)
    (VERIFY_OUT / f"{phase_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: verify.py <phase_id> [iteration]", file=sys.stderr)
        return 2
    iteration = int(argv[2]) if len(argv) > 2 else 0
    rep = verify(argv[1], iteration)
    print(f"[verify] {rep['phase']} (iter {iteration}) → {'PASS' if rep['passed'] else 'FAIL'}", file=sys.stderr)
    for c in rep["checks"]:
        print(f"  {'✓' if c['ok'] else '✗'} {c['name']}: {c['detail'][:90]}", file=sys.stderr)
    print(json.dumps(rep, ensure_ascii=False))
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
