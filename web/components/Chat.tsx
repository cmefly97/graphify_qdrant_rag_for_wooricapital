"use client";
import { useEffect, useState } from "react";
import SourceBadge from "./SourceBadge";
import EvidenceGraph from "./EvidenceGraph";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";

type Answer = {
  answer: string; route: string; mode: string; confidence: string;
  sources: { source_file?: string; effective_date?: string }[];
  evidence_nodes: string[];
};

export default function Chat({ preset }: { preset: string | null }) {
  const [q, setQ] = useState("");
  const [resp, setResp] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (preset) { setQ(preset); ask(preset); } }, [preset]);

  async function ask(query: string) {
    setLoading(true); setResp(null);
    try {
      const r = await fetch(`${API}/ask`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      setResp(await r.json());
    } finally { setLoading(false); }
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 8 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="질문을 입력하세요" style={{ flex: 1, padding: 10 }}
          onKeyDown={(e) => e.key === "Enter" && ask(q)} />
        <button onClick={() => ask(q)} disabled={loading} style={{ padding: "10px 16px" }}>
          {loading ? "검색 중…" : "질문"}
        </button>
      </div>
      {resp && (
        <div style={{ marginTop: 16, border: "1px solid #eee", borderRadius: 8, padding: 16 }}>
          <div style={{ whiteSpace: "pre-wrap" }}>{resp.answer}</div>
          <div style={{ marginTop: 8, fontSize: 12, color: "#888" }}>
            라우팅: {resp.route} · 모드: {resp.mode} · 신뢰도: {resp.confidence}
          </div>
          <div style={{ marginTop: 8 }}>
            {resp.sources?.map((s, i) => <SourceBadge key={i} source={s} />)}
          </div>
          {resp.evidence_nodes?.length > 0 && <EvidenceGraph nodes={resp.evidence_nodes} />}
        </div>
      )}
    </div>
  );
}
