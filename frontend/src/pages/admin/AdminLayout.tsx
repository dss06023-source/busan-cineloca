// 관리자 화면 공통(UI-10~12): 위쪽 메뉴, 로그인이 풀리면(401) 로그인 화면으로.
import { useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router";
import { ApiError, endpoints } from "../../api/client";

export function isUnauthorized(e: unknown): boolean {
  return e instanceof ApiError && e.status === 401;
}

export function AdminLayout() {
  const nav = useNavigate();
  const qc = useQueryClient();
  return (
    <div className="admin">
      <header className="admin-bar">
        <strong>씨네로케 관리</strong>
        <nav aria-label="관리 메뉴">
          <NavLink to="/admin/sync">동기화</NavLink>
          <NavLink to="/admin/reviews">검수</NavLink>
        </nav>
        <button
          type="button"
          className="button"
          onClick={async () => {
            await endpoints.adminLogout().catch(() => undefined);
            qc.clear();
            nav("/admin/login");
          }}
        >
          로그아웃
        </button>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
