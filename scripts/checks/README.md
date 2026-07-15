# scripts/checks — phase별 커스텀 검증

`verify.py` 는 `scripts/checks/<phase_id>_check.py` 가 있으면 그 안의
`check(root: Path) -> list[dict]` 를 호출한다. 각 dict 형식:

```python
{"name": "체크명", "ok": True/False, "detail": "설명", "blocking": True/False}
```

- `blocking=True` 체크가 하나라도 실패하면 그 phase 는 FAIL.
- 파일이 없으면 outputs+pytest 기본 검증만 수행한다.
- 실제 산출물이 아직 없을 땐 "없으면 통과(skip)" 로 작성해, 구현 전에는 방해하지 않게 한다.
