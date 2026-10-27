// UI-10 동기화 리포트(FR-612·613): 최근 10회 실행, 건수 가드 경고, 실패 목록, 오늘 AI 호출 수.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router";
import { endpoints, type SyncReport } from "../../api/client";
import { isUnauthorized } from "./AdminLayout";

const STATUS: Record<string, string> = {
  requested: "대기",
  running: "실행 중",
  published: "반영됨",
  rejected: "가드 위반·미반영",
  failed: "실패",
};

type Run = SyncReport["runs"][number];

function countsText(r: Run): string {
  const c = Object.entries(r.counts ?? {}).filter(([k, v]) => k !== "guard" && typeof v === "number");
  if (!c.length) return "-";
  return c.map(([k, v]) => `${k} ${v}${r.prev_counts && typeof r.prev_counts[k] === "number" ? ` (직전 ${r.prev_counts[k]})` : ""}`).join(", ");
}

export function AdminSync() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-sync"], queryFn: endpoints.syncReport, refetchInterval: 15000 });
  const req = useMutation({ mutationFn: endpoints.requestSync, onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-sync"] }) });
  if (isUnauthorized(q.error)) return <Navigate to="/admin/login" replace />;
  const busy = q.data?.runs.some((r) => r.status === "requested" || r.status === "running");
  return (
    <section>
      <h1>동기화</h1>
      <p>
        <button type="button" className="primary" disabled={busy || req.isPending} onClick={() => req.mutate()}>
          {busy ? "동기화 대기·실행 중" : "지금 동기화 요청"}
        </button>
        <span className="muted"> 배치가 1분 안에 요청을 가져갑니다. 건수 가드를 통과해야 서비스 데이터가 바뀝니다.</span>
      </p>
      {q.isError && <p className="error">{(q.error as Error).message}</p>}
      {q.data && (
        <>
          <p className="muted">
            오늘 AI 호출:{" "}
            {Object.entries(q.data.usage).map(([k, v]) => `${k.replace("gemini:", "")} ${v}회`).join(", ") || "0회"}
          </p>
          {q.data.runs.length === 0 && <p className="muted">아직 실행 기록이 없습니다.</p>}
          <ul className="list" aria-label="동기화 기록">
            {q.data.runs.map((r) => (
              <li key={r.id} className="card">
                <strong>
                  #{r.id} {STATUS[r.status] ?? r.status}
                </strong>
                <span className="muted"> · {r.trigger === "manual" ? "수동" : "정기"}</span>
                <div className="muted">{countsText(r)}</div>
                {r.guard && r.guard.ok === false && <p className="error">건수 가드 위반: {String(r.guard.reason ?? "")}</p>}
                {Array.isArray(r.failures) && r.failures.length > 0 && (
                  <details>
                    <summary>실패 {r.failures.length}건</summary>
                    <ul>
                      {r.failures.map((f, i) => (
                        <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
