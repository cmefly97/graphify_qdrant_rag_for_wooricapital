"use client";
import { useEffect, useRef } from "react";

/**
 * 근거 그래프 패널 — 답변이 거친 그래프 노드를 Cytoscape 로 시각화.
 * 중앙 '질의' 노드에 근거 노드들을 연결해 보여준다(간단한 star 레이아웃).
 */
export default function EvidenceGraph({ nodes }: { nodes: string[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let cy: any;
    (async () => {
      const cytoscape = (await import("cytoscape")).default;
      if (!ref.current) return;
      const elements: any[] = [{ data: { id: "Q", label: "질의" } }];
      nodes.slice(0, 12).forEach((n, i) => {
        elements.push({ data: { id: `n${i}`, label: n } });
        elements.push({ data: { source: "Q", target: `n${i}` } });
      });
      cy = cytoscape({
        container: ref.current, elements,
        style: [
          { selector: "node", style: { label: "data(label)", "font-size": 9, "background-color": "#6688ff", color: "#222", "text-wrap": "wrap", "text-max-width": "90px" } },
          { selector: "node[id='Q']", style: { "background-color": "#ff8844" } },
          { selector: "edge", style: { width: 1, "line-color": "#bbb" } },
        ],
        layout: { name: "concentric", minNodeSpacing: 30 },
      });
    })();
    return () => cy?.destroy();
  }, [nodes]);

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>근거 그래프</div>
      <div ref={ref} style={{ height: 240, border: "1px solid #eee", borderRadius: 8 }} />
    </div>
  );
}
