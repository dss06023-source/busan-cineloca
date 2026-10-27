// 완주 배지(FR-508): 코스의 모든 장소 스탬프가 있으면 API-018이 배지를 준다.
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router";
import { endpoints, type BadgeIn, type RouteOut } from "../api/client";
import { addBadge, stampTokens } from "../lib/stamps";

type Props = { course: BadgeIn["course"]; title: string; stops: RouteOut["stops"] };

export function BadgeButton({ course, title, stops }: Props) {
  const run = useMutation({
    mutationFn: async () => {
      const r = await endpoints.badge({ course, stamps: stampTokens() });
      if (r.ok && r.token) addBadge({ token: r.token, title });
      return r;
    },
  });
  const names = Object.fromEntries(stops.map((s) => [s.location_id, s.name]));
  const r = run.data;
  return (
    <div className="card" aria-label="완주 배지">
      <button type="button" className="button" disabled={run.isPending || r?.ok === true} onClick={() => run.mutate()}>
        {r?.ok ? "배지를 받았습니다" : "완주 배지 받기"}
      </button>
      {r?.ok && (
        <p className="notice">
          완주 배지를 받았습니다. <Link to="/me">스탬프북 보기</Link>
        </p>
      )}
      {r && !r.ok && <p className="muted">아직 인증하지 않은 곳: {r.missing.map((id) => names[id] ?? `#${id}`).join(", ")}</p>}
      {run.isError && <p className="error">{(run.error as Error).message}</p>}
    </div>
  );
}
