// AI 문장 표시(FR-707): 'AI 생성', 강등이면 '기본 정보로 대체됨', 마스킹이면 그 사실도(FR-702).
export function AiLabel({ degraded = false, masked = false }: { degraded?: boolean; masked?: boolean }) {
  return (
    <span className="ai-label">
      {degraded ? "기본 정보로 대체됨" : "AI 생성"}
      {masked && " · 개인정보를 가리고 보냈습니다"}
    </span>
  );
}
