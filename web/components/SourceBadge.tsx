export default function SourceBadge({ source }: { source: { source_file?: string; effective_date?: string } }) {
  if (!source?.source_file) return null;
  return (
    <span style={{
      display: "inline-block", background: "#f0f4ff", border: "1px solid #c7d6ff",
      borderRadius: 12, padding: "2px 10px", margin: "2px 4px 0 0", fontSize: 12,
    }}>
      📄 {source.source_file}{source.effective_date ? ` · ${source.effective_date}` : ""}
    </span>
  );
}
