// 사용자 화면 공통: 하단 탭 5개(지도·작품·AI 탐색·코스·내 기록).
import { NavLink, Outlet } from "react-router";

const TABS = [
  { to: "/", label: "지도", end: true },
  { to: "/works", label: "작품" },
  { to: "/ask", label: "AI 탐색" },
  { to: "/courses", label: "코스" },
  { to: "/me", label: "내 기록" },
];

export function Layout() {
  return (
    <div className="app">
      <main className="content">
        <Outlet />
      </main>
      <nav className="tabs" aria-label="주 메뉴">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? "tab active" : "tab")}>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
