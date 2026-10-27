// 역 이름 표시. 원본에 '부산역'처럼 '역'이 붙은 이름이 있어 두 번 붙이지 않는다(백엔드 station_label과 같은 규칙).
export function stationLabel(name: string, line?: string | null): string {
  const base = name.endsWith("역") ? name : `${name}역`;
  return line ? `${base}(${line})` : base;
}

// 부산 도시철도 노선색(DESIGN.md). 데이터 색으로만 쓴다(역 배지, 코스 이동 구간).
const LINE_COLORS: { key: string; bg: string; fg: string }[] = [
  { key: "1호선", bg: "#f06a00", fg: "#000" },
  { key: "2호선", bg: "#81bf48", fg: "#fff" },
  { key: "3호선", bg: "#bb8c00", fg: "#000" },
  { key: "4호선", bg: "#217dcb", fg: "#fff" },
  { key: "경전철", bg: "#8652a1", fg: "#fff" },
  { key: "동해선", bg: "#0c8e72", fg: "#fff" },
];

export function lineColor(line?: string | null): { bg: string; fg: string } | null {
  if (!line) return null;
  return LINE_COLORS.find((c) => line.includes(c.key)) ?? null;
}
