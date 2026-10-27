import { describe, expect, it } from "vitest";
import { probe } from "./geo";

function fakeGeo(impl: (ok: PositionCallback, fail: PositionErrorCallback) => void): Geolocation {
  return { getCurrentPosition: impl, watchPosition: () => 0, clearWatch: () => {} } as unknown as Geolocation;
}

describe("probe", () => {
  it("위치를 얻으면 좌표와 정확도를 돌려준다", async () => {
    const geo = fakeGeo((ok) => ok({ coords: { latitude: 35.1, longitude: 129.0, accuracy: 12 } } as GeolocationPosition));
    expect(await probe(geo)).toEqual({ lat: 35.1, lon: 129.0, accuracy: 12 });
  });
  it("거부되면 null(부산역 기준으로 대체)", async () => {
    const geo = fakeGeo((_, fail) => fail({ code: 1 } as GeolocationPositionError));
    expect(await probe(geo)).toBeNull();
  });
  it("위치 기능이 없으면 null", async () => {
    expect(await probe(undefined)).toBeNull();
  });
});
