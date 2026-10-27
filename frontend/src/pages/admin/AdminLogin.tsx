// UI-10 관리자 로그인(FR-615). 5회 실패하면 10분 잠금(423).
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { ApiError, endpoints } from "../../api/client";

export function loginError(e: unknown): string {
  if (e instanceof ApiError && e.status === 423) {
    const min = Math.ceil((e.retryAfter ?? 600) / 60);
    return `로그인 시도가 많아 막았습니다. 약 ${min}분 뒤에 다시 시도해 주세요.`;
  }
  if (e instanceof ApiError && e.status === 401) return "비밀번호가 맞지 않습니다. 5회 틀리면 10분 동안 막힙니다.";
  return e instanceof Error ? e.message : "로그인하지 못했습니다.";
}

export function AdminLogin() {
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const login = useMutation({ mutationFn: endpoints.adminLogin, onSuccess: () => nav("/admin/sync") });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (pw) login.mutate(pw);
  }
  return (
    <section className="page narrow">
      <h1>관리자 로그인</h1>
      <form className="card filters" onSubmit={submit}>
        <label>
          비밀번호
          <input type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
        </label>
        <button type="submit" className="primary" disabled={!pw || login.isPending}>
          로그인
        </button>
        {login.isError && <p className="error">{loginError(login.error)}</p>}
      </form>
    </section>
  );
}
