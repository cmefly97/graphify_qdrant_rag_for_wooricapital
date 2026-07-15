"use client";
import { useState } from "react";
import Chat from "../components/Chat";

const EXAMPLES = [
  "론/할부 상품 취급 가능 개월수가 어떻게돼?",
  "론/할부 나이스 885점, 금리등급 2등급일 때 적용 될 수 있는 최저 금리 알려줘",
  "듀얼상품 금리등급 몇등급까지 취급 가능해?",
  "엔카 슬라이딩 가능해?",
  "신용회복, 개인회생 고객인데 판정값이 R 판정이야",
];

export default function Page() {
  const [preset, setPreset] = useState<string | null>(null);
  return (
    <main style={{ maxWidth: 880, margin: "0 auto", padding: 24, fontFamily: "system-ui" }}>
      <h1>우리캐피탈 오토운영팀 상담챗봇</h1>
      <p style={{ color: "#666" }}>중고오토리스·심사·운영기준 질의응답 (근거·출처 제공)</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, margin: "12px 0" }}>
        {EXAMPLES.map((q) => (
          <button key={q} onClick={() => setPreset(q)}
            style={{ border: "1px solid #ccc", borderRadius: 16, padding: "6px 12px", cursor: "pointer" }}>
            {q}
          </button>
        ))}
      </div>
      <Chat preset={preset} />
    </main>
  );
}
