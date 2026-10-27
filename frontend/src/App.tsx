import { useEffect, useState } from "react";
import { describeHealth, fetchHealth, type Health } from "./health";

// WP-01 자리표시 화면. 하단 탭 5개와 지도 홈은 WP-04가 만든다.
export default function App() {
  const [health, setHealth] = useState<Health | null | undefined>(undefined);

  useEffect(() => {
    fetchHealth().then(setHealth);
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 16, maxWidth: 480, margin: "0 auto" }}>
      <h1>부산 씨네로케</h1>
      <p>영화·드라마 속 부산 촬영지 안내 서비스(개발 중)</p>
      <p>{health === undefined ? "상태 확인 중…" : describeHealth(health)}</p>
    </main>
  );
}
