// 첫 화면. 넓은 화면(1100px 이상)에서는 왼쪽 AI 탐색, 가운데 지도, 오른쪽 작품·코스를 한 화면에 둔다.
// 좁은 화면은 지금처럼 지도 홈만 보여 주고 나머지는 하단 탭으로 간다.
import { useState } from "react";
import { useMediaQuery, WIDE_QUERY } from "../lib/media";
import { Ask } from "./Ask";
import { Courses } from "./Courses";
import { MapHome } from "./MapHome";
import { Works } from "./Works";

const SIDE_TABS = [
  { id: "works", label: "작품" },
  { id: "courses", label: "코스" },
] as const;
type SideTab = (typeof SIDE_TABS)[number]["id"];

export function Home() {
  const wide = useMediaQuery(WIDE_QUERY);
  const [side, setSide] = useState<SideTab>("works");
  if (!wide) return <MapHome />;
  return (
    <div className="home">
      <aside className="pane pane-ask" aria-label="AI 탐색 패널">
        <Ask embedded />
      </aside>
      <section className="pane pane-map" aria-label="지도 패널">
        <MapHome />
      </section>
      <aside className="pane pane-side" aria-label="작품·코스 패널">
        <div className="pane-tabs" role="tablist" aria-label="오른쪽 패널">
          {SIDE_TABS.map((t) => (
            <button key={t.id} type="button" role="tab" aria-selected={side === t.id} onClick={() => setSide(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
        {side === "works" ? <Works /> : <Courses />}
      </aside>
    </div>
  );
}
