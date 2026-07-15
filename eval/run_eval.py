"""평가 러너 — 골든셋으로 정확도·출처·환각률 측정 → eval/report.md.

지표:
- 정확도: expect 문자열이 모두 답변에 포함되면 정답.
- 수치 정확도: type=numeric 항목의 정답률(상담 사고 방지의 핵심).
- 출처율: 정답 답변에 출처가 붙은 비율.
- 환각 회피: type=unknown 은 mode 가 none/context_only(추측 답변 금지)면 정답.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.api import answer_query

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "goldenset.jsonl"
REPORT = ROOT / "eval" / "report.md"


def load() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate() -> dict:
    items = load()
    rows, passed, num_total, num_pass, src_ok, src_total = [], 0, 0, 0, 0, 0
    for it in items:
        r = answer_query(it["query"])
        if it["type"] == "unknown":
            # 핵심은 '환각 없이 거절했는가'. mode 가 none 이거나(단축),
            # LLM 경로라도 '규정에 명시되어 있지 않습니다'로 거절했으면 정답.
            ok = (r["mode"] in it.get("expect_mode", ["none"])) or ("규정에 명시되어 있지 않습니다" in r["answer"])
        else:
            ok = all(s in r["answer"] for s in it.get("expect", []))
        passed += int(ok)
        if it["type"] == "numeric":
            num_total += 1
            num_pass += int(ok)
        if ok and it["type"] != "unknown":
            src_total += 1
            src_ok += int(bool(r.get("sources")))
        rows.append({"id": it["id"], "type": it["type"], "ok": ok, "mode": r["mode"],
                     "answer": r["answer"][:80].replace("\n", " ")})
    return {
        "total": len(items), "passed": passed,
        "accuracy": round(passed / len(items), 3),
        "numeric_accuracy": round(num_pass / num_total, 3) if num_total else None,
        "source_rate": round(src_ok / src_total, 3) if src_total else None,
        "rows": rows,
    }


def write_report(m: dict) -> None:
    lines = [
        "# 평가 리포트 (골든셋)", "",
        f"- 전체 정확도: **{m['accuracy']:.0%}** ({m['passed']}/{m['total']})",
        f"- 수치형 정확도: **{m['numeric_accuracy']:.0%}** (환각 0 목표)",
        f"- 출처 첨부율: **{m['source_rate']:.0%}**", "",
        "| id | type | 결과 | mode | 답변(요약) |", "|---|---|---|---|---|",
    ]
    for r in m["rows"]:
        lines.append(f"| {r['id']} | {r['type']} | {'✅' if r['ok'] else '❌'} | {r['mode']} | {r['answer']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    m = evaluate()
    write_report(m)
    print(json.dumps({k: v for k, v in m.items() if k != "rows"}, ensure_ascii=False))
