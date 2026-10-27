// 역 배지: 노선색 바탕에 노선 이름과 역 이름. 색만으로 구분하지 않도록 노선 이름 글자를 함께 쓴다.
import { lineColor, stationLabel } from "../lib/station";

export function StationBadge({ name, line }: { name: string; line?: string | null }) {
  const c = lineColor(line);
  const base = stationLabel(name);
  if (!c) return <span className="station">{line ? stationLabel(name, line) : base}</span>;
  return (
    <span className="station">
      <span className="line-chip" style={{ background: c.bg, color: c.fg }}>
        {line}
      </span>
      {base}
    </span>
  );
}
