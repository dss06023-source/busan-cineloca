// UI-07 코스 상세(FR-302): 추천 코스(/courses/:id)와 저장 코스(/courses/saved/:key).
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";
import { endpoints } from "../api/client";
import { BadgeButton } from "../components/BadgeButton";
import { RouteView } from "../components/RouteView";
import { getSaved, MAX_SAVED, saveCourse } from "../lib/savedCourses";

export function CourseDetail() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["course", id], queryFn: () => endpoints.course(id), enabled: Number.isInteger(id) });
  const [saved, setSaved] = useState<"idle" | "ok" | "full">("idle");
  if (q.isLoading) return <p className="page muted">불러오는 중…</p>;
  if (q.isError || !q.data) return <p className="page error">{(q.error as Error)?.message ?? "찾는 정보가 없습니다."}</p>;
  const { course, route } = q.data;
  return (
    <article className="page">
      <h1>{course.title}</h1>
      <p className="muted">{course.start_label} 출발</p>
      <RouteView route={route} />
      <button
        type="button"
        className="button"
        disabled={saved === "ok"}
        onClick={() => setSaved(saveCourse({ route, title: course.title, kind: "recommended" }) ? "ok" : "full")}
      >
        {saved === "ok" ? "저장했습니다" : "이 코스 저장"}
      </button>
      {saved === "full" && <p className="error">코스는 {MAX_SAVED}개까지 저장됩니다.</p>}
      <BadgeButton course={{ id: course.id }} title={course.title} stops={route.stops} />
    </article>
  );
}

export function SavedCourseDetail() {
  const c = getSaved(useParams().key ?? "");
  if (!c) return <p className="page error">저장한 코스를 찾을 수 없습니다.</p>;
  return (
    <article className="page">
      <h1>{c.title}</h1>
      <p className="muted">이 브라우저에 저장한 코스입니다({new Date(c.savedAt).toLocaleDateString("ko-KR")}).</p>
      <RouteView route={c.route} />
      <BadgeButton course={{ location_ids: c.route.stops.map((s) => s.location_id) }} title={c.title} stops={c.route.stops} />
    </article>
  );
}
