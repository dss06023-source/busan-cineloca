// 방문 인증 버튼(FR-501~505): 고정밀 위치 → API-016. 좌표는 이 요청에만 쓰고 저장하지 않는다.
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router";
import { ApiError, endpoints, type CertifyOut } from "../api/client";
import { probe } from "../lib/geo";
import { addStamp, stampTokens } from "../lib/stamps";

export const MAX_ACCURACY_M = 50; // BR-07

export function failText(r: CertifyOut, radius: number): string {
  if (r.reason === "accuracy") return `위치 정확도가 낮습니다(${MAX_ACCURACY_M}m 초과). 실외로 나가 잠시 뒤 다시 시도해 주세요.`;
  if (r.reason === "duplicate") return "이미 스탬프를 받은 곳입니다.";
  return `촬영지에서 약 ${r.distance_m}m 떨어져 있습니다. ${radius}m 안으로 가까이 가서 다시 시도해 주세요.`;
}

export function CertifyButton({ locationId, radius }: { locationId: number; radius: number }) {
  const run = useMutation({
    mutationFn: async () => {
      const pos = await probe();
      if (!pos) throw new ApiError(0, "GEO");
      const r = await endpoints.certify({ location_id: locationId, lat: pos.lat, lon: pos.lon, accuracy_m: pos.accuracy, held: stampTokens() });
      if (r.ok && r.token) addStamp(r.token);
      return r;
    },
  });
  const r = run.data;
  return (
    <div>
      <button type="button" className="primary" disabled={run.isPending || r?.ok === true} onClick={() => run.mutate()}>
        {run.isPending ? "위치 확인 중…" : r?.ok ? "인증했습니다" : "방문 인증하기"}
      </button>
      <p className="muted">반경 {radius}m 안에서, 위치 정확도 {MAX_ACCURACY_M}m 이내일 때 인증됩니다. 위치는 저장하지 않습니다.</p>
      {r?.ok && (
        <p className="notice">
          스탬프를 받았습니다. <Link to="/me">스탬프북 보기</Link>
        </p>
      )}
      {r && !r.ok && <p className="error">{failText(r, radius)}</p>}
      {run.isError && (
        <p className="error">
          {run.error instanceof ApiError && run.error.code === "GEO"
            ? "현재 위치를 알 수 없습니다. 위치 권한을 허용한 뒤 다시 시도해 주세요."
            : (run.error as Error).message}
        </p>
      )}
    </div>
  );
}
