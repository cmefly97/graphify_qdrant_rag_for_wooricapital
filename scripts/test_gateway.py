#!/usr/bin/env python3
"""게이트웨이 실연결 점검 — 사내망에서 실행한다.

.env 의 키/엔드포인트로 Octen 임베딩 + HCX/Qwen chat 을 호출해 정상 응답을 확인한다.
키는 .env 에서만 읽으며 출력하지 않는다.

사용: (사내망에서) python scripts/test_gateway.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from app.gateway.client import GatewayClient  # noqa: E402


def _trial(label: str, fn) -> bool:
    t0 = time.time()
    try:
        print(f"[{label}] OK ({time.time() - t0:.1f}s): {fn()}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[{label}] FAIL ({time.time() - t0:.1f}s): {type(e).__name__}: {str(e)[:200]}")
        return False


def main() -> int:
    s = get_settings()
    print("chat key:", s.has_gateway_key, "| embed key:", s.has_embedding_key,
          "| embed:", s.embedding_base_url, "| chat:", s.hcx30_base_url)
    gc = GatewayClient(s)
    ok = []
    ok.append(_trial("EMBED " + s.embedding_model, lambda: f"dim={len(gc.embed('테스트 임베딩'))}"))
    ok.append(_trial("CHAT " + s.hcx30_model,
                     lambda: gc.chat([{"role": "user", "content": "한 문장으로 인사해줘."}], model=s.hcx30_model)[:120]))
    ok.append(_trial("CHAT " + s.qwen_model,
                     lambda: gc.chat([{"role": "user", "content": "한 문장으로 인사해줘."}], model=s.qwen_model)[:120]))
    print(f"\n결과: {sum(ok)}/{len(ok)} 통과")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
