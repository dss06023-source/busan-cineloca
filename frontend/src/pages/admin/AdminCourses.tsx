// UI-12 추천 코스 관리(FR-614): 테마로 후보를 만들고, 장소 순서를 고쳐 다시 계산하고, 승인하면 공개된다.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router";
import { endpoints, type AdminCourse, type CourseDraftIn } from "../../api/client";
import { formatMinutes } from "../../components/RouteView";
import { adminError, isUnauthorized } from "./AdminLayout";

const THEMES: { value: CourseDraftIn["theme"]; label: string; hint: string }[] = [
  { value: "area", label: "지역", hint: "구·군 이름(예: 중구)" },
  { value: "work", label: "작품", hint: "작품 ID" },
  { value: "actor", label: "인물", hint: "인물 ID" },
];

/** 장소 순서를 i번째와 i+d번째를 바꿔 돌려준다. 범위를 벗어나면 그대로. */
export function move<T>(list: T[], i: number, d: -1 | 1): T[] {
  const j = i + d;
  if (j < 0 || j >= list.length) return list;
  const next = [...list];
  [next[i], next[j]] = [next[j], next[i]];
  return next;
}

function legText(s: AdminCourse["stops"][number]): string {
  if (!s.leg_mode) return "";
  return s.leg_mode === "subway" ? `도시철도 ${s.leg_line ?? ""} ${s.leg_min}분` : `도보 ${s.leg_min}분`;
}

function CourseCard({ course }: { course: AdminCourse }) {
  const qc = useQueryClient();
  const [order, setOrder] = useState(course.stops.map((s) => s.location_id));
  const names = Object.fromEntries(course.stops.map((s) => [s.location_id, s.name ?? `#${s.location_id}`]));
  const edit = useMutation({
    mutationFn: endpoints.editCourse,
    onSuccess: (c) => {
      setOrder(c.stops.map((s) => s.location_id));
      qc.invalidateQueries({ queryKey: ["admin-courses"] });
    },
  });
  const changed = order.join() !== course.stops.map((s) => s.location_id).join();
  const approved = course.status === "approved";
  return (
    <li className="card" aria-label={`코스 ${course.id}`}>
      <p>
        <strong>{course.title}</strong> <span className={approved ? "badge" : "badge muted"}>{approved ? "공개" : "초안"}</span>
      </p>
      <p className="muted">
        {course.start_label} 출발 · 총 {formatMinutes(course.total_min)} · {(course.total_m / 1000).toFixed(1)}km
      </p>
      <ol aria-label="장소 순서">
        {order.map((id, i) => {
          const stop = course.stops.find((s) => s.location_id === id);
          return (
            <li key={id}>
              {names[id]} {!changed && stop && <span className="muted">({legText(stop)})</span>}{" "}
              <button type="button" className="button" aria-label={`${names[id]} 위로`} disabled={i === 0} onClick={() => setOrder(move(order, i, -1))}>
                ↑
              </button>
              <button type="button" className="button" aria-label={`${names[id]} 아래로`} disabled={i === order.length - 1} onClick={() => setOrder(move(order, i, 1))}>
                ↓
              </button>
              <button type="button" className="button" aria-label={`${names[id]} 빼기`} disabled={order.length <= 3} onClick={() => setOrder(order.filter((x) => x !== id))}>
                빼기
              </button>
            </li>
          );
        })}
      </ol>
      <p>
        {changed && (
          <button type="button" className="primary" disabled={edit.isPending} onClick={() => edit.mutate({ id: course.id, stops: order })}>
            이 순서로 다시 계산
          </button>
        )}{" "}
        {approved ? (
          <button type="button" className="button" disabled={edit.isPending} onClick={() => edit.mutate({ id: course.id, status: "draft" })}>
            공개 내리기
          </button>
        ) : (
          <button type="button" className="primary" disabled={edit.isPending || changed} onClick={() => edit.mutate({ id: course.id, status: "approved" })}>
            승인
          </button>
        )}
      </p>
      {changed && <p className="muted">순서를 바꾸면 다시 계산한 뒤 초안으로 돌아가며, 다시 승인해야 공개됩니다.</p>}
      {edit.isError && <p className="error">{adminError(edit.error)}</p>}
    </li>
  );
}

function DraftForm() {
  const qc = useQueryClient();
  const [theme, setTheme] = useState<CourseDraftIn["theme"]>("area");
  const [ref, setRef] = useState("");
  const [title, setTitle] = useState("");
  const draft = useMutation({
    mutationFn: endpoints.draftCourse,
    onSuccess: () => {
      setRef("");
      setTitle("");
      qc.invalidateQueries({ queryKey: ["admin-courses"] });
    },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (ref.trim()) draft.mutate({ theme, ref: ref.trim(), title: title.trim() || null });
  }
  return (
    <form className="card filters" onSubmit={submit} aria-label="코스 후보 만들기">
      <h2>후보 만들기</h2>
      <p className="muted">테마에 맞는 촬영지를 작품 수 순으로 5곳 골라 경로를 계산합니다. 사유지는 넣지 않습니다.</p>
      <label>
        테마
        <select value={theme} onChange={(e) => setTheme(e.target.value as CourseDraftIn["theme"])}>
          {THEMES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        대상
        <input placeholder={THEMES.find((t) => t.value === theme)!.hint} value={ref} onChange={(e) => setRef(e.target.value)} />
      </label>
      <label>
        제목(비우면 자동)
        <input maxLength={60} value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <button type="submit" className="primary" disabled={!ref.trim() || draft.isPending}>
        후보 만들기
      </button>
      {draft.isSuccess && <p className="notice">초안을 만들었습니다: {draft.data.title}</p>}
      {draft.isError && <p className="error">{adminError(draft.error)}</p>}
    </form>
  );
}

export function AdminCourses() {
  const q = useQuery({ queryKey: ["admin-courses"], queryFn: endpoints.adminCourses });
  if (isUnauthorized(q.error)) return <Navigate to="/admin/login" replace />;
  return (
    <section>
      <h1>추천 코스</h1>
      <DraftForm />
      {q.isError && <p className="error">{adminError(q.error)}</p>}
      {q.data?.items.length === 0 && <p className="muted">코스가 없습니다.</p>}
      <ul className="list" aria-label="코스 목록">
        {q.data?.items.map((c) => <CourseCard key={`${c.id}:${c.stops.map((s) => s.location_id).join()}`} course={c} />)}
      </ul>
    </section>
  );
}
