// UI-05 AI 탐색(FR-401~412): 질의 → 해석 조건 칩·결과 목록·지도·요약. AI가 강등되면 FilterPanel을 prefill로 연다.
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError, endpoints, type Criteria, type MapItem, type QueryOut } from "../api/client";
import { AiLabel } from "../components/AiLabel";
import { FilterPanel } from "../components/FilterPanel";
import { MapView } from "../components/MapView";
import { useNotice } from "../components/NoticeGate";
import { SourceCards } from "../components/SourceCard";
import { EMPTY, withChoice, withoutField, type ChipField } from "../lib/criteria";
import { probe } from "../lib/geo";

export const MAX_LEN = 200; // FR-401
export const EXAMPLES = [
  "강도윤 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안",
  "해운대구에서 찍은 로맨스 영화 촬영지",
  "서면역에서 걸어서 15분 안에 갈 수 있는 촬영지",
  "2010년 이후 개봉한 액션 영화 촬영지",
];
const HERE_WORDS = ["여기", "내 위치", "현재 위치", "지금 위치", "근처", "주변"];
const RELAX_TEXT: Record<string, string> = { travel: "이동 조건", years: "개봉연도", genres: "장르", gus: "구·군" };
const BUSAN_STATION = { lat: 35.1152, lon: 129.0422 };

type Run = { kind: "ask"; text: string } | { kind: "search"; criteria: Criteria; labels: Record<string, string> };

export function Ask() {
  const [accepted] = useNotice();
  const [text, setText] = useState("");
  const [panel, setPanel] = useState<Criteria | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [noMap, setNoMap] = useState(false);

  const run = useMutation({
    mutationFn: async (r: Run): Promise<QueryOut> => {
      if (r.kind === "search") return endpoints.search(r.criteria, r.labels);
      const wantsHere = HERE_WORDS.some((w) => r.text.includes(w));
      const pos = wantsHere ? await probe() : null;
      return endpoints.ask(r.text, pos && { lat: pos.lat, lon: pos.lon });
    },
    onSuccess: (out, r) => {
      setLabels({ ...(r.kind === "search" ? r.labels : {}), ...out.labels });
      // AI 장애·찾지 못함이면 필터 패널을 열고 조건을 미리 채운다(FR-405·411)
      if (out.status === "FALLBACK" || out.status === "NOT_FOUND") setPanel(out.prefill ?? EMPTY);
      else if (r.kind === "ask") setPanel(null);
    },
  });

  const out = run.data;
  const tooLong = text.length > MAX_LEN;

  function submit(e: FormEvent) {
    e.preventDefault();
    const t = text.trim();
    if (!t || tooLong || !accepted) return;
    run.mutate({ kind: "ask", text: t });
  }

  function research(c: Criteria) {
    run.mutate({ kind: "search", criteria: c, labels });
  }

  async function newChat() {
    await endpoints.resetQuery().catch(() => undefined);
    run.reset();
    setPanel(null);
    setText("");
  }

  const mapItems: MapItem[] = (out?.items ?? [])
    .filter((i) => i.lat != null && i.lon != null)
    .map((i) => ({ id: i.id, name: i.name, lat: i.lat!, lon: i.lon!, distance_m: i.distance_m, works: i.works, work_count: i.works.length, station: null }));

  return (
    <section className="page">
      <div className="toolbar">
        <h1 style={{ flex: 1, margin: 0 }}>AI 탐색</h1>
        <button type="button" className="button" onClick={newChat}>
          새 대화
        </button>
      </div>
      <form onSubmit={submit}>
        <textarea
          className="query"
          aria-label="질문"
          rows={3}
          value={text}
          placeholder="예: 강도윤 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안"
          onChange={(e) => setText(e.target.value)}
          disabled={!accepted}
        />
        <div className="toolbar">
          <span className={tooLong ? "error" : "muted"} aria-live="polite">
            {text.length}/{MAX_LEN}
            {tooLong && " · 200자 이내로 줄여 주세요."}
          </span>
          <button type="submit" className="primary" disabled={!accepted || tooLong || !text.trim() || run.isPending}>
            {run.isPending ? "찾는 중…" : "찾기"}
          </button>
          <button type="button" className="button" onClick={() => setPanel(panel ? null : (out?.criteria ?? EMPTY))}>
            {panel ? "필터 닫기" : "직접 고르기"}
          </button>
        </div>
      </form>
      {!out && !run.isPending && (
        <ul className="examples" aria-label="예시 질의">
          {EXAMPLES.map((ex) => (
            <li key={ex}>
              <button type="button" className="link" onClick={() => setText(ex)}>
                {ex}
              </button>
            </li>
          ))}
        </ul>
      )}
      {run.isError && <p className="error">{run.error instanceof ApiError ? run.error.message : "요청을 처리하지 못했습니다."}</p>}

      {out && <Status out={out} />}
      {out && out.chips.length > 0 && out.criteria && (
        <ul className="tags" aria-label="해석한 조건">
          {out.chips.map((c) => (
            <li key={c.field}>
              {c.label}{" "}
              <button type="button" aria-label={`${c.label} 조건 빼기`} onClick={() => research(withoutField(out.criteria!, c.field as ChipField))}>
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      {out?.status === "NEEDS_CHOICE" && out.prefill && (
        <div className="card" role="group" aria-label="후보 고르기">
          <p>어느 것을 찾으셨나요?</p>
          <div className="toolbar">
            {out.choices.map((ch) => (
              <button key={`${ch.field}-${ch.value}`} type="button" className="button" onClick={() => research(withChoice(out.prefill!, ch.field, ch.value))}>
                {ch.label}
              </button>
            ))}
          </div>
        </div>
      )}
      {out?.notices.map((n) => (
        <p key={n} className="notice">
          {n}
        </p>
      ))}
      {panel && <FilterPanel key={JSON.stringify(panel)} initial={panel} labels={labels} onSearch={research} busy={run.isPending} />}

      {out?.summary && (
        <div className="card" aria-label="AI 요약">
          <AiLabel masked={out.masked} />
          {out.summary.sentences.map((s, i) => (
            <p key={i}>{s}</p>
          ))}
        </div>
      )}
      {out && !out.summary && out.masked && <p className="muted">개인정보를 가리고 보냈습니다.</p>}

      {mapItems.length > 0 && !noMap && (
        <MapView center={mapItems[0] ?? BUSAN_STATION} items={mapItems} onSelect={() => undefined} onUnavailable={() => setNoMap(true)} />
      )}
      {out && out.items.length > 0 && (
        <ul className="list" aria-label="검색 결과">
          {out.items.map((i) => (
            <li key={i.id}>
              <Link className="list-item" to={`/locations/${i.id}`}>
                <strong>{i.name}</strong>
                <span className="muted">
                  {[i.gu, i.travel_min != null && `약 ${Math.round(i.travel_min)}분`, i.works.map((w) => w.title).join(", ")].filter(Boolean).join(" · ")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {out && out.works.length > 0 && (
        <ul className="list" aria-label="작품 결과">
          {out.works.map((w) => (
            <li key={w.id}>
              <Link className="list-item" to={`/works/${w.id}`}>
                <strong>{w.title}</strong>
                <span className="muted">{[w.release_year, `촬영지 ${w.location_count}곳`].filter(Boolean).join(" · ")}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {out && <SourceCards sources={out.sources} />}
    </section>
  );
}

function Status({ out }: { out: QueryOut }) {
  switch (out.status) {
    case "FALLBACK":
      return <p className="notice">AI가 질문을 해석하지 못했습니다. 아래에서 조건을 직접 골라 주세요.</p>;
    case "OUT_OF_SCOPE":
      return <p className="notice">부산의 영화·드라마 촬영지와 작품에 대해서만 답할 수 있습니다.</p>;
    case "NOT_FOUND":
      return <p className="notice">조건에 맞는 촬영지를 찾지 못했습니다. 조건을 바꿔 다시 찾아 주세요.</p>;
    case "RELAXED":
      return <p className="notice">결과가 없어 {out.relaxed.map((r) => RELAX_TEXT[r]).join(", ")} 조건을 풀었습니다.</p>;
    default:
      return null;
  }
}
