// 사용자 화면 공통: 하단 탭 5개(지도·작품·AI 탐색·코스·내 기록), 상세 화면의 뒤로 가기, 탭 제목, 스크롤 위치 복원.
import { useEffect } from "react";
import { NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from "react-router";

const TABS = [
  { to: "/", label: "지도", end: true },
  { to: "/works", label: "작품" },
  { to: "/ask", label: "AI 탐색" },
  { to: "/courses", label: "코스" },
  { to: "/me", label: "내 기록" },
];

const APP_NAME = "부산 씨네로케";

// 상세 화면 경로 → 바로 가기가 없을 때(링크로 바로 들어옴) 돌아갈 목록
const DETAILS: { prefix: string; parent: string; title: string }[] = [
  { prefix: "/locations/", parent: "/", title: "촬영지" },
  { prefix: "/works/", parent: "/works", title: "작품" },
  { prefix: "/courses/", parent: "/courses", title: "코스" },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "지도",
  "/works": "작품",
  "/ask": "AI 탐색",
  "/courses": "코스",
  "/me": "내 기록",
  "/sources": "데이터 출처·이용 안내",
};

export function pageTitle(pathname: string): string {
  const name = PAGE_TITLES[pathname] ?? DETAILS.find((d) => pathname.startsWith(d.prefix))?.title;
  return name ? `${name} · ${APP_NAME}` : APP_NAME;
}

function BackBar({ parent }: { parent: string }) {
  const nav = useNavigate();
  const { key } = useLocation();
  // 앱 안에서 넘어왔으면 이전 화면으로(목록 스크롤 위치도 복원), 바로 들어왔으면 목록으로
  const back = () => (key !== "default" ? nav(-1) : nav(parent));
  return (
    <div className="back-bar">
      <button type="button" className="link-button" onClick={back}>
        ← 뒤로
      </button>
    </div>
  );
}

export function Layout() {
  const { pathname } = useLocation();
  const detail = DETAILS.find((d) => pathname.startsWith(d.prefix));

  useEffect(() => {
    document.title = pageTitle(pathname);
  }, [pathname]);

  return (
    <div className="app">
      <main className="content">
        {detail && <BackBar parent={detail.parent} />}
        <Outlet />
      </main>
      <nav className="tabs" aria-label="주 메뉴">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? "tab active" : "tab")}>
            {t.label}
          </NavLink>
        ))}
      </nav>
      <ScrollRestoration />
    </div>
  );
}
