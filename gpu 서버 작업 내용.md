Accessing workspace:

 /root/jinkyu_dev

 Quick safety check: Is this a project you created or one you trust? (Like your own code, a well-known open
 source project, or work from your team). If not, take a moment to review what's in this folder first.

 Claude Code'll be able to read, edit, and execute files here.

 Security guide

 ❯ 1. Yes, I trust this folder ✔
Resume this session with:
claude --resume f77050ea-50bc-4b32-9664-76be18401dc1
root@testa100:~/jinkyu_dev#  cat /root/jinkyu_dev/vllm-serving-notes.md
# vLLM 서빙 구성 기록 (A100 서버)

- **작성일**: 2026-07-15
- **서버 공인 IP**: `211.188.49.10`
- **GPU**: NVIDIA A100-SXM4-80GB × 8 (index 0~7)
- **드라이버 / CUDA**: 570.211.01 / CUDA 12.8
- **컨테이너 런타임**: Docker 29.6.1 + NVIDIA Container Toolkit 1.19.1
- **공통 이미지**: `vllm/vllm-openai:latest` (= **vLLM 0.25.1**)

---

## 1. 오늘 수행한 작업 요약

1. **환경 구축 (신규 설치)**
   - Docker CE 설치 (공식 apt 저장소) → 데몬 active
   - NVIDIA Container Toolkit 설치 및 `nvidia` 런타임 등록 (`nvidia-ctk runtime configure --runtime=docker`)
   - 컨테이너에서 GPU 접근 정상 검증
2. **Qwen3.6-35B-A3B 서빙** — GPU 6+7 텐서 병렬, 포트 8000 (라이브)
3. **임베딩 모델 2종 서빙** — GPU 5 한 장에 컨테이너 2개, 포트 8001 / 8002
4. 세 서버 모두 OpenAI 호환 API 제공

---

## 2. 세 모델 서빙 정보 (핵심 표)

| 항목 | Qwen3.6-35B-A3B | bge-m3 | Octen-Embedding-8B |
|------|-----------------|--------|--------------------|
| 컨테이너명 | `qwen35-vllm` | `bge-m3-vllm` | `octen-embed-vllm` |
| HF repo | `Qwen/Qwen3.6-35B-A3B` | `BAAI/bge-m3` | `Octen/Octen-Embedding-8B` |
| 용도 | Chat / VLM (텍스트·이미지·비디오) | 임베딩 | 임베딩 |
| 아키텍처 | `Qwen3_5MoeForConditionalGeneration` (하이브리드 linear-attn MoE) | `XLMRobertaModel` | `Qwen3Model` |
| 가중치(bf16) | ~71.9 GB | 2.27 GB | 15.13 GB |
| GPU | **6 + 7** (TP=2) | **5** | **5** |
| 외부 포트 | **8000** | **8001** | **8002** |
| 컨테이너 내부 포트 | 8000 | 8000 | 8000 |
| runner | generate (기본) | pooling | pooling |
| max-model-len | 32768 | 8192 | 8192 |
| gpu-memory-utilization | 0.90 | 0.10 | 0.35 |
| 임베딩 차원 | — | 1024 | 4096 |
| vLLM 지원 | 네이티브 ✅ | 네이티브 ✅ (`BgeM3EmbeddingModel`) | Transformers 백엔드 경유 (폴백 옵션 없이 정상 로드) ✅ |
| 상태 (2026-07-15 검증) | **LIVE ✅** | **LIVE ✅** | **LIVE ✅** |

> 검증: 세 서버 모두 `/health` OK, 임베딩 2종은 실제 벡터 반환 확인(bge-m3 1024차원 / Octen 4096차원), Qwen `/v1/models` 응답 확인.
> GPU 실측 점유: **GPU 5 = 약 29 GB** (임베딩 2종 합산, 80GB 중), GPU 6·7 = 각 ~74 GB (Qwen TP2).

---

## 3. 외부 접근 URL (공인 IP `211.188.49.10`)

| 모델 | Base URL | 주요 엔드포인트 |
|------|----------|------------------|
| Qwen3.6-35B-A3B | `http://211.188.49.10:8000/v1` | `/chat/completions`, `/completions`, `/models` |
| bge-m3 | `http://211.188.49.10:8001/v1` | `/embeddings`, `/models` |
| Octen-Embedding-8B | `http://211.188.49.10:8002/v1` | `/embeddings`, `/models` |

> ⚠️ 외부에서 실제 접속하려면 **NAVER Cloud 방화벽(ACG)에서 8000~8002 인바운드 허용** 필요.

### 호출 예시

```bash
# Qwen 채팅
curl http://211.188.49.10:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3.6-35B-A3B","messages":[{"role":"user","content":"안녕"}]}'

# bge-m3 임베딩
curl http://211.188.49.10:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"BAAI/bge-m3","input":"임베딩할 문장"}'

# Octen 임베딩
curl http://211.188.49.10:8002/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"Octen/Octen-Embedding-8B","input":"임베딩할 문장"}'
```

```python
from openai import OpenAI
client = OpenAI(base_url="http://211.188.49.10:8000/v1", api_key="EMPTY")
print(client.chat.completions.create(
    model="Qwen/Qwen3.6-35B-A3B",
    messages=[{"role": "user", "content": "안녕"}],
).choices[0].message.content)
```

---

## 4. GPU 할당 맵

| GPU | 사용 |
|-----|------|
| 0, 1 | (기존 타 작업 프로세스) |
| 2, 3, 4 | 여유 |
| **5** | bge-m3 + Octen-Embedding-8B (임베딩 2종 공유) |
| **6, 7** | Qwen3.6-35B-A3B (텐서 병렬) |

**GPU 5에 임베딩 2종 동시 서빙 가능 여부 → 가능.**
- 가중치 합계 ~17.4 GB / 80 GB로 여유 큼.
- 단, vLLM 1컨테이너=1모델이므로 컨테이너 2개 + 포트 분리 필요.
- 기본 `gpu-memory-utilization 0.9`면 첫 컨테이너가 GPU를 독점하므로 반드시 낮게 분배 (0.10 / 0.35 적용).

---

## 5. 실행 명령어 (재현용)

`HF_TOKEN`은 파일에 저장하지 않고 실행 시점 환경변수로만 주입 (env var only).

```bash
# 공통: HF 캐시 디렉토리
mkdir -p /root/.cache/huggingface

# (1) Qwen3.6-35B-A3B  — GPU 6+7
HF_TOKEN=<token> docker run -d --name qwen35-vllm \
  --gpus '"device=6,7"' --ipc=host -p 8000:8000 -e HF_TOKEN \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3.6-35B-A3B --tensor-parallel-size 2 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 --port 8000

# (2) bge-m3  — GPU 5
HF_TOKEN=<token> docker run -d --name bge-m3-vllm \
  --gpus '"device=5"' --ipc=host -p 8001:8000 -e HF_TOKEN \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model BAAI/bge-m3 --runner pooling \
  --max-model-len 8192 --gpu-memory-utilization 0.10 --port 8000

# (3) Octen-Embedding-8B  — GPU 5
HF_TOKEN=<token> docker run -d --name octen-embed-vllm \
  --gpus '"device=5"' --ipc=host -p 8002:8000 -e HF_TOKEN \
  -v /root/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Octen/Octen-Embedding-8B --runner pooling \
  --max-model-len 8192 --gpu-memory-utilization 0.35 --port 8000
```

---

## 6. 운영 명령어

```bash
docker ps                              # 실행 중 컨테이너
docker logs -f <name>                  # 로그 실시간
docker restart <name>                  # 재시작 (캐시된 가중치라 빠름)
docker stop <name> && docker rm <name> # 중지 + 제거
nvidia-smi -i 5,6,7                     # GPU 사용량
curl -sf http://localhost:<port>/health && echo OK   # 헬스체크
```

---

## 7. 주의사항 / 트러블슈팅 메모

- **⚠️ 보안**: 세 서버 모두 현재 **인증 없이** 공인 IP에 노출. 권장 조치:
  1. `-e VLLM_API_KEY=<키>` 로 API 키 설정 (요청 시 `Authorization: Bearer <키>` 필요)
  2. 방화벽에서 8000~8002 포트를 신뢰 IP 대역으로 제한
- **vLLM 0.25.1 플래그 변경**: 구버전 `--task embed` → **제거됨**. 임베딩은 `--runner pooling` 사용. (`--task` 지정 시 즉시 `unrecognized arguments` 에러로 컨테이너 종료)
- **Octen-Embedding-8B**: config 아키텍처가 `Qwen3Model`이라 vLLM 네이티브 등록이 없어 **Transformers 백엔드 폴백**으로 로드됨. 로드 실패 시 `--model-impl transformers` 옵션 추가 검토.
- **Qwen3.6-35B-A3B**: 가중치 72GB라 A100 80GB **단일 카드로는 부적합**(KV 캐시 공간 부족) → 텐서 병렬 2장으로 구성.
- **HF 캐시 공유**: 세 컨테이너가 `/root/.cache/huggingface` 볼륨 공유. 재시작 시 재다운로드 없음.
- **텐서 병렬 시 `--ipc=host` 필수** (NCCL shared memory).