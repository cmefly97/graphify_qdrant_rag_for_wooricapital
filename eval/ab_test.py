"""A/B 회귀 테스트 하네스 (운영 전환 항목 5).

골든셋 평가 결과를 베이스라인 스냅샷(eval/baseline.json)과 비교해 업그레이드 전후
항목별 개선/회귀/답변변경을 보고한다. 업그레이드(추출·조회·프롬프트·임베딩 변경)마다
실행해 '무엇이 좋아지고 무엇이 깨졌는지'를 조기에 잡는다.

사용:
  python eval/ab_test.py --save-baseline   # 현재를 베이스라인(A)으로 저장
  python eval/ab_test.py                    # 현재(B) vs 베이스라인(A) 비교
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
BASELINE = ROOT / "eval" / "baseline.json"


def _rows_to_map(rows: list[dict]) -> dict:
    return {r["id"]: {"ok": r["ok"], "mode": r["mode"], "answer": r["answer"]} for r in rows}


def save_baseline(rows: list[dict], path: Path = BASELINE) -> None:
    path.write_text(json.dumps(_rows_to_map(rows), ensure_ascii=False, indent=2), encoding="utf-8")


def load_baseline(path: Path = BASELINE) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def compare(current_rows: list[dict], baseline: dict) -> dict:
    cur = _rows_to_map(current_rows)
    improved, regressed, changed, newly = [], [], [], []
    for qid, c in cur.items():
        b = baseline.get(qid)
        if b is None:
            newly.append(qid)
            continue
        if c["ok"] and not b["ok"]:
            improved.append(qid)
        elif b["ok"] and not c["ok"]:
            regressed.append(qid)
        elif c["answer"] != b["answer"]:
            changed.append(qid)
    removed = [qid for qid in baseline if qid not in cur]
    return {
        "improved": improved, "regressed": regressed, "answer_changed": changed,
        "new": newly, "removed": removed,
        "same": len(cur) - len(improved) - len(regressed) - len(changed) - len(newly),
    }


def main(argv: list[str]) -> int:
    from eval.run_eval import evaluate

    m = evaluate()
    rows = m["rows"]
    if "--save-baseline" in argv:
        save_baseline(rows)
        print(f"[ab] 베이스라인 저장: {len(rows)}문항 (accuracy={m['accuracy']})")
        return 0
    base = load_baseline()
    if base is None:
        save_baseline(rows)
        print("[ab] 베이스라인이 없어 현재를 베이스라인으로 저장했습니다. 다음 변경부터 비교됩니다.")
        return 0
    diff = compare(rows, base)
    print(f"[ab] A(baseline) vs B(current) — accuracy={m['accuracy']} numeric={m['numeric_accuracy']}")
    print(f"  개선 {len(diff['improved'])} {diff['improved']}")
    print(f"  회귀 {len(diff['regressed'])} {diff['regressed']}")
    print(f"  답변변경 {len(diff['answer_changed'])} {diff['answer_changed']}")
    print(f"  신규 {len(diff['new'])} / 제거 {len(diff['removed'])} / 동일 {diff['same']}")
    return 1 if diff["regressed"] else 0  # 회귀가 있으면 실패 신호


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
