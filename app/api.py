"""질의 API — 라우팅→확장→(테이블|검색)→재랭킹→생성 파이프라인.

POST /ask {query} → {answer, sources, route, evidence_nodes, mode, confidence}
"""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import (
    expander as qexpander,
    generator,
    logging_store,
    reranker,
    retriever,
    router as qrouter,
    tables_lookup,
)
from app.gateway.client import GatewayClient

api_router = APIRouter()
_gc = GatewayClient()


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str
    route: str
    mode: str
    confidence: str
    sources: list[dict]
    evidence_nodes: list[str]
    evidence: dict = {}
    trace: list[dict] = []
    query_id: str = ""


class FeedbackRequest(BaseModel):
    query_id: str
    vote: str  # "up" | "down"


def answer_query(query: str, with_trace: bool = False) -> dict:
    trace: list[dict] = []

    def step(name: str, detail: str, t0: float, **extra) -> None:
        if with_trace:
            trace.append({"step": name, "detail": detail,
                          "ms": round((time.perf_counter() - t0) * 1000, 1), **extra})

    # 1) 라우팅
    t = time.perf_counter()
    route = qrouter.classify(query)
    step("질의 라우팅", f"분류 결과: {route}", t)

    # 2) 쿼리 확장(동의어/유사표현)
    t = time.perf_counter()
    variants = qexpander.expand(query)
    step("쿼리 확장", f"동의어·유사표현 {len(variants)}개 생성", t, items=variants[:6])

    # 3) 구조화 테이블 조회(정밀 수치의 정답원, 환각 0)
    t = time.perf_counter()
    table_result = tables_lookup.lookup(query)
    step("구조화 테이블 조회(tables.db)",
         ("매칭됨 → 수치/규칙 정답 확보" if table_result else "매칭 없음 → 벡터·그래프 경로로"),
         t, hit=bool(table_result))

    # 4) 하이브리드 검색: 벡터 유사도 → 그래프 탐색
    #    트레이스 표시(또는 테이블 미스/설명형)일 때 수행
    contexts, evidence_nodes, graph_sources = [], [], []
    if with_trace or table_result is None or route in ("descriptive", "mixed"):
        retrieved = retriever.retrieve(query, _gc)
        contexts = retrieved["contexts"]
        evidence_nodes = retrieved["evidence_nodes"]
        graph_sources = retrieved.get("graph_sources", [])
        vh = retrieved["vector_hits"]
        if with_trace:
            trace.append({"step": "벡터 유사도 검색(Qdrant/임베딩)",
                          "detail": f"상위 {len(vh)}개 청크 검색 (의미 기반 시작점)",
                          "ms": retrieved["timings"]["vector_ms"],
                          "items": [f"{h['score']} · {h['source_file']}" for h in vh]})
            trace.append({"step": "그래프 탐색(NetworkX)",
                          "detail": f"시작 문서 {len(retrieved['seed_files'])}개 → 연결 노드 {len(evidence_nodes)}개 확장",
                          "ms": retrieved["timings"]["graph_ms"],
                          "items": evidence_nodes[:8]})

    # 5) 재랭킹
    t = time.perf_counter()
    ranked = reranker.rerank(contexts, table_result)
    step("재랭킹 + 출처 부착", f"근거 {len(ranked)}건 정렬(테이블 우선)", t)

    # 6) 답변 생성
    t = time.perf_counter()
    result = generator.generate(query, route, table_result, ranked if not table_result else [], _gc)
    step("답변 생성", f"모드={result['mode']} · 신뢰도={result['confidence']}", t)

    return {
        "answer": result["answer"],
        "route": route,
        "mode": result["mode"],
        "confidence": result["confidence"],
        "sources": result["sources"],
        "evidence_nodes": evidence_nodes,
        "evidence": {
            "chunks": [{"text": c["text"], "source_file": c["source"].get("source_file"),
                        "doc_type": c["source"].get("doc_type"), "score": c["score"]}
                       for c in contexts[:4]],
            "graph": graph_sources[:8],
        },
        "trace": trace,
    }


CHAT_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>우리캐피탈 오토운영팀 상담챗봇</title>
<style>
:root{--blue:#3b5bdb;--line:#e6e8eb}
*{box-sizing:border-box}
body{font-family:system-ui,Apple SD Gothic Neo,sans-serif;margin:0;color:#222;height:100vh;display:flex;flex-direction:column}
header{padding:12px 20px;border-bottom:1px solid var(--line)}
header h1{font-size:18px;margin:0}header .sub{color:#777;font-size:12px}
.wrap{flex:1;display:flex;min-height:0}
.center{flex:1;display:flex;flex-direction:column;min-width:0;border-right:1px solid var(--line)}
.right{width:340px;min-width:280px;display:flex;flex-direction:column;background:#fafbfc;overflow-y:auto;border-right:1px solid var(--line)}
.right2{border-right:none}
.center{min-width:320px}
.right h2{font-size:13px;margin:0;padding:11px 16px;border-bottom:1px solid var(--line);border-top:1px solid var(--line);color:#444;background:#f2f4f8;position:sticky;top:0}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:12px 16px;border-bottom:1px solid var(--line)}
.chip{border:1px solid #ccd;border-radius:16px;padding:5px 11px;font-size:12px;cursor:pointer;background:#f7f8ff}
.chip:hover{background:#eef1ff}
#log{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{padding:10px 14px;border-radius:12px;max-width:88%}
.u{align-self:flex-end;background:var(--blue);color:#fff}
.a{align-self:flex-start;background:#f1f3f5;border:1px solid var(--line)}
.ans{white-space:pre-wrap}.meta{font-size:11px;color:#888;margin-top:6px}
.badge{display:inline-block;background:#eef4ff;border:1px solid #c7d6ff;border-radius:10px;padding:1px 8px;margin:3px 4px 0 0;font-size:11px}
.nodes{margin-top:6px;font-size:11px;color:#556}
.fb{margin-top:6px}.fb button{border:1px solid #ddd;background:#fff;border-radius:8px;cursor:pointer;font-size:13px;margin-right:6px}
.bar{display:flex;gap:8px;padding:12px 16px;border-top:1px solid var(--line)}
.bar input{flex:1;padding:10px;border:1px solid #ccd;border-radius:8px}
.bar button{padding:10px 16px;border:0;background:var(--blue);color:#fff;border-radius:8px;cursor:pointer}
#trace{padding:10px 14px}
#evi{padding:10px 14px}
.echunk{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px;background:#fff}
.echunk .eh{font-size:11px;color:#3b5bdb;font-weight:700;margin-bottom:4px}
.echunk .et{font-size:11.5px;color:#444;white-space:pre-wrap;max-height:120px;overflow:auto;line-height:1.45}
.enode{display:inline-block;background:#f3faf5;border:1px solid #bfe3cd;border-radius:8px;padding:3px 8px;margin:3px 4px 0 0;font-size:11px}
.enode small{color:#6b7280}
.tstep{border:1px solid var(--line);border-left:3px solid var(--blue);border-radius:8px;padding:8px 10px;margin-bottom:8px;background:#fff;opacity:0;transform:translateY(6px);transition:.25s}
.tstep.show{opacity:1;transform:none}
.tstep.skip{border-left-color:#bbb;opacity:.6}
.tstep .h{display:flex;justify-content:space-between;font-size:12px;font-weight:600}
.tstep .ms{color:#3a8;font-weight:500}
.tstep .d{font-size:11px;color:#666;margin-top:3px}
.tstep ul{margin:5px 0 0;padding-left:16px}.tstep li{font-size:11px;color:#555;word-break:break-all}
.empty{color:#aaa;font-size:12px;padding:8px}
a.dash{font-size:12px;color:var(--blue)}
</style></head><body>
<header><h1>우리캐피탈 오토운영팀 상담챗봇</h1>
<div class="sub">중앙: 질문/답변 · 우측: 데이터 질의→검색→내부처리 과정 · <a class="dash" href="/dashboard" target="_blank">운영 대시보드</a></div></header>
<div class="wrap">
  <div class="center">
    <div class="chips" id="chips"></div>
    <div id="log"></div>
    <div class="bar"><input id="q" placeholder="질문을 입력하세요 (예: 금리등급 2등급 최저금리)" autofocus>
    <button onclick="ask()">질문</button></div>
  </div>
  <div class="right">
    <h2>🔎 처리 과정 (파이프라인 트레이스)</h2>
    <div id="trace"><div class="empty">질문하면 라우팅→쿼리확장→테이블조회→벡터검색→그래프탐색→재랭킹→생성 단계가 순서대로 표시됩니다.</div></div>
  </div>
  <div class="right right2">
    <h2>📄 답변 근거 (청크 & graphify 출처)</h2>
    <div id="evi"><div class="empty">답변이 참조한 실제 청크 원문과 graphify 그래프 노드·출처가 표시됩니다.</div></div>
  </div>
</div>
<script>
const EX=["론/할부 취급 가능 개월수가 어떻게돼?","금리등급 2등급 최저금리 알려줘",
"듀얼상품 금리등급 몇등급까지 취급 가능해?","엔카 슬라이딩 가능해?",
"중형트럭 취급톤수 조건","재고금융 대상물품","그랜져 2.4 잔가군","성능점검기록부 확인 기준"];
const chips=document.getElementById('chips');
EX.forEach(q=>{const b=document.createElement('div');b.className='chip';b.textContent=q;b.onclick=()=>{document.getElementById('q').value=q;ask();};chips.appendChild(b);});
const log=document.getElementById('log'), traceEl=document.getElementById('trace'), eviEl=document.getElementById('evi');
function add(cls,html){const d=document.createElement('div');d.className='msg '+cls;d.innerHTML=html;log.appendChild(d);d.scrollIntoView();return d;}
function esc(s){return (s||'').replace(/</g,'&lt;');}
function renderTrace(trace){
  traceEl.innerHTML='';
  if(!trace||!trace.length){traceEl.innerHTML='<div class=empty>처리 단계 정보가 없습니다.</div>';return;}
  trace.forEach((t,i)=>{
    const skip=/매칭 없음|생략/.test(t.detail)&&/조회/.test(t.step);
    const items=(t.items&&t.items.length)?'<ul>'+t.items.map(x=>`<li>${esc(String(x))}</li>`).join('')+'</ul>':'';
    const el=document.createElement('div');el.className='tstep'+(skip?' skip':'');
    el.innerHTML=`<div class=h><span>${i+1}. ${esc(t.step)}</span><span class=ms>${t.ms} ms</span></div>`+
      `<div class=d>${esc(t.detail)}</div>`+items;
    traceEl.appendChild(el);
    setTimeout(()=>el.classList.add('show'), i*220);  // 순차 등장 → 처리과정 체감
  });
}
function renderEvidence(ev){
  eviEl.innerHTML='';
  if(!ev||((!ev.chunks||!ev.chunks.length)&&(!ev.graph||!ev.graph.length))){
    eviEl.innerHTML='<div class=empty>근거 정보가 없습니다.</div>';return;}
  const chunks=ev.chunks||[];
  eviEl.insertAdjacentHTML('beforeend','<div class=sm style="margin:2px 0 6px;color:#888">▍ 답변 추출 청크 ('+chunks.length+')</div>');
  chunks.forEach((c,i)=>{
    eviEl.insertAdjacentHTML('beforeend',
      `<div class=echunk><div class=eh>청크 ${i+1} · 유사도 ${c.score} · ${esc(c.source_file||'')}${c.doc_type?' ('+esc(c.doc_type)+')':''}</div>`+
      `<div class=et>${esc(c.text||'')}</div></div>`);
  });
  const g=ev.graph||[];
  eviEl.insertAdjacentHTML('beforeend','<div class=sm style="margin:10px 0 6px;color:#888">▍ graphify 노드 · 출처</div>');
  eviEl.insertAdjacentHTML('beforeend', g.length
    ? g.map(n=>`<span class=enode>🔗 ${esc(n.label||'')}<br><small>${esc(n.source_file||'-')}</small></span>`).join('')
    : '<div class=empty>연결 노드 없음</div>');
}
async function ask(){
  const q=document.getElementById('q').value.trim(); if(!q)return;
  add('u',esc(q)); document.getElementById('q').value='';
  const wait=add('a','검색 중…');
  traceEl.innerHTML='<div class=empty>처리 중…</div>';
  eviEl.innerHTML='<div class=empty>처리 중…</div>';
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});
    const s=await r.json();
    const src=(s.sources||[]).filter(x=>x&&x.source_file).map(x=>`<span class=badge>📄 ${esc(x.source_file)}${x.effective_date?' · '+x.effective_date:''}</span>`).join('');
    const nodes=(s.evidence_nodes||[]).length?`<div class=nodes>🔗 근거 노드: ${esc(s.evidence_nodes.slice(0,8).join(', '))}</div>`:'';
    wait.innerHTML=`<div class=ans>${esc(s.answer)}</div>`+
      `<div class=meta>라우팅 ${s.route} · 모드 ${s.mode} · 신뢰도 ${s.confidence}</div>`+src+nodes+
      `<div class=fb><button onclick="fb('${s.query_id}','up',this)">👍</button><button onclick="fb('${s.query_id}','down',this)">👎</button></div>`;
    renderTrace(s.trace); renderEvidence(s.evidence);
  }catch(e){wait.innerHTML='오류: '+e;traceEl.innerHTML='<div class=empty>오류</div>';eviEl.innerHTML='<div class=empty>오류</div>';}
}
async function fb(id,v,btn){await fetch('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query_id:id,vote:v})});btn.parentElement.innerHTML='피드백 감사합니다 ('+(v==='up'?'👍':'👎')+')';}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')ask();});
</script></body></html>"""


@api_router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    t0 = time.time()
    result = answer_query(req.query, with_trace=True)
    result["query"] = req.query
    qid = logging_store.log_query(result, int((time.time() - t0) * 1000))
    return AskResponse(query_id=qid, **{k: result[k] for k in
                       ("answer", "route", "mode", "confidence", "sources", "evidence_nodes", "evidence", "trace")})


@api_router.post("/feedback")
def feedback(req: FeedbackRequest) -> dict:
    ok = logging_store.set_feedback(req.query_id, req.vote)
    return {"ok": ok}


@api_router.get("/stats")
def stats() -> dict:
    return logging_store.stats()


@api_router.get("/", response_class=HTMLResponse)
def chat_page() -> str:
    return CHAT_HTML


@api_router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>상담챗봇 운영 대시보드</title>
<style>body{font-family:system-ui;max-width:900px;margin:24px auto;padding:0 16px}
h1{font-size:20px}table{border-collapse:collapse;width:100%;margin:8px 0}
td,th{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:14px}
.card{display:inline-block;border:1px solid #e0e0e0;border-radius:8px;padding:12px 18px;margin:6px}
.card b{font-size:22px;display:block}</style></head><body>
<h1>우리캐피탈 오토운영팀 상담챗봇 — 운영 대시보드</h1>
<div id="cards"></div><h3>모드 분포</h3><div id="modes"></div>
<h3>피드백</h3><div id="fb"></div><h3>빈출 질의 Top</h3><table id="top"></table>
<script>
fetch('/stats').then(r=>r.json()).then(s=>{
  document.getElementById('cards').innerHTML =
    `<div class=card>총 질의<b>${s.total_queries}</b></div>`+
    `<div class=card>규정無 반환율<b>${(s.no_evidence_rate*100).toFixed(1)}%</b></div>`+
    `<div class=card>평균 지연<b>${s.avg_latency_ms} ms</b></div>`;
  document.getElementById('modes').innerHTML =
    Object.entries(s.by_mode||{}).map(([k,v])=>`<span class=card>${k}<b>${v}</b></span>`).join('');
  document.getElementById('fb').innerHTML =
    `👍 ${ (s.feedback&&s.feedback.up)||0 }  /  👎 ${ (s.feedback&&s.feedback.down)||0 }`;
  document.getElementById('top').innerHTML =
    '<tr><th>질의</th><th>횟수</th></tr>'+(s.top_queries||[]).map(t=>`<tr><td>${t.query}</td><td>${t.count}</td></tr>`).join('');
});
</script></body></html>"""
