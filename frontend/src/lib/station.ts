// 역 이름 표시. 원본에 '부산역'처럼 '역'이 붙은 이름이 있어 두 번 붙이지 않는다(백엔드 station_label과 같은 규칙).
export function stationLabel(name: string, line?: string | null): string {
  const base = name.endsWith("역") ? name : `${name}역`;
  return line ? `${base}(${line})` : base;
}
