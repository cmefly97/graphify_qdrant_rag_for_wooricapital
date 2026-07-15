"""회귀 게이트 임계 — 스케줄러·CI 공용 단일 출처.

수치 정확도는 절대 후퇴 불가(100%), 전체 정확도·출처율 임계.
"""
from __future__ import annotations

THRESHOLDS = {"numeric_accuracy": 1.0, "accuracy": 0.95, "source_rate": 1.0}


def regression_gate(metrics: dict, thresholds: dict | None = None) -> tuple[bool, list[str]]:
    th = thresholds or THRESHOLDS
    fails = []
    for k, lo in th.items():
        v = metrics.get(k)
        if v is None or v < lo:
            fails.append(f"{k}={v} < {lo}")
    return (not fails), fails
