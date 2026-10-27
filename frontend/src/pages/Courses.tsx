// UI-06 코스(FR-301~313): 추천 코스 · 나만의 코스 · AI 맞춤 코스 탭. 만든 코스는 브라우저에 저장(최대 10개).
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError, endpoints, type AICourseIn, type AICourseOut, type RouteOut, type StartIn } from "../api/client";
import { AiLabel } from "../components/AiLabel";
import { useNotice } from "../components/NoticeGate";
import { formatMinutes, RouteView } from "../components/RouteView";
import { probe } from "../lib/geo";
import { listSaved, MAX_SAVED, removeSaved, saveCourse, type SavedCourse } from "../lib/savedCourses";
import { stationLabel } from "../lib/station";

const TABS = [
  { id: "recommended", label: "추천 코스" },
  { id: "custom", label: "나만의 코스" },
  { id: "ai", label: "AI 맞춤" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export function Courses() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("tab"))?.id ?? "recommended") as Tab;
  const [saved, setSaved] = useState<SavedCourse[]>(listSaved);

  return (
    <section className="page">
      <h1>코스</h1>
      <div className="segmented" role="tablist" aria-label="코스 종류">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} aria-pressed={tab === t.id} onClick={() => setParams({ tab: t.id })}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "recommended" && <Recommended />}
      {tab === "custom" && <Custom onSaved={() => setSaved(listSaved())} />}
      {tab === "ai" && <AiCourse onSaved={() => setSaved(listSaved())} />}
      <SavedList
        saved={saved}
        onRemove={(k) => {
          removeSaved(k);
          setSaved(listSaved());
        }}
      />
    </section>
  );
}

function Recommended() {
  const [theme, setTheme] = useState("");
  const q = useQuery({ queryKey: ["courses", theme], queryFn: () => endpoints.courses(theme || undefined) });
  return (
    <div>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <select aria-label="테마" value={theme} onChange={(e) => setTheme(e.target.value)}>
          <option value="">모든 테마</option>
          <option value="work">작품</option>
          <option value="actor">배우</option>
          <option value="area">지역</option>
        </select>
      </div>
      {q.isError && <p className="error">{(q.error as Error).message}</p>}
      {q.data && q.data.items.length === 0 && <p className="muted">추천 코스가 아직 없습니다.</p>}
      <ul className="list" aria-label="추천 코스 목록">
        {q.data?.items.map((c) => (
          <li key={c.id}>
            <Link className="list-item" to={`/courses/${c.id}`}>
              <strong>{c.title}</strong>
              <span className="muted">
                {c.start_label} 출발 · {c.stop_count}곳 · {formatMinutes(c.total_min)} · {(c.total_m / 1000).toFixed(1)}km
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StartPicker({ value, onChange, allowText = false }: { value: string; onChange: (v: string) => void; allowText?: boolean }) {
  const meta = useQuery({ queryKey: ["meta"], queryFn: endpoints.meta, staleTime: Infinity });
  return (
    <label>
      출발지
      <select aria-label="출발지" value={value} onChange={(e) => onChange(e.target.value)}>
        {allowText && <option value="">문장에서 / 부산역</option>}
        <option value="here">현재 위치</option>
        {meta.data?.stations.map((s) => (
          <option key={s.id} value={s.id}>
            {stationLabel(s.name, s.line)}
          </option>
        ))}
      </select>
    </label>
  );
}

async function toStart(v: string): Promise<StartIn | null> {
  if (!v) return null;
  if (v !== "here") return { station_id: v };
  const pos = await probe();
  if (!pos) throw new ApiError(0, "GEO");
  return { lat: pos.lat, lon: pos.lon };
}

function SaveButton({ route, title, kind, onSaved }: { route: RouteOut; title: string; kind: SavedCourse["kind"]; onSaved: () => void }) {
  const [state, setState] = useState<"idle" | "saved" | "full">("idle");
  return (
    <p>
      <button
        type="button"
        className="button"
        disabled={state === "saved"}
        onClick={() => {
          const ok = saveCourse({ route, title, kind });
          setState(ok ? "saved" : "full");
          if (ok) onSaved();
        }}
      >
        {state === "saved" ? "저장했습니다" : "이 코스 저장"}
      </button>
      {state === "full" && <span className="error"> 코스는 {MAX_SAVED}개까지 저장됩니다. 저장한 코스를 지운 뒤 다시 저장해 주세요.</span>}
    </p>
  );
}

function errorText(e: unknown): string {
  if (e instanceof ApiError && e.code === "GEO") return "현재 위치를 알 수 없습니다. 출발 역을 골라 주세요.";
  return e instanceof ApiError ? e.message : "요청을 처리하지 못했습니다.";
}

function Custom({ onSaved }: { onSaved: () => void }) {
  const meta = useQuery({ queryKey: ["meta"], queryFn: endpoints.meta, staleTime: Infinity });
  const [start, setStart] = useState("113");
  const [gu, setGu] = useState("중구");
  const [picked, setPicked] = useState<{ id: number; name: string }[]>([]);
  const places = useQuery({ queryKey: ["gu-places", gu], queryFn: () => endpoints.searchLocations({ base: { gu }, radius_m: 1000, filters: {} }) });
  const plan = useMutation({
    mutationFn: async ({ ids, fixed }: { ids: number[]; fixed: boolean }) => {
      const s = (await toStart(start))!;
      return endpoints.planCourse({ start: s, location_ids: ids, fixed_order: fixed });
    },
  });

  function toggle(p: { id: number; name: string }) {
    setPicked((cur) => (cur.some((x) => x.id === p.id) ? cur.filter((x) => x.id !== p.id) : cur.length >= 10 ? cur : [...cur, p]));
  }

  function move(i: number, dir: -1 | 1) {
    const ids = plan.data!.stops.map((s) => s.location_id);
    [ids[i], ids[i + dir]] = [ids[i + dir], ids[i]];
    plan.mutate({ ids, fixed: true });
  }

  return (
    <div>
      <div className="card filters">
        <StartPicker value={start} onChange={setStart} />
        <label>
          구·군
          <select aria-label="구·군" value={gu} onChange={(e) => setGu(e.target.value)}>
            {meta.data?.districts.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <div className="checks" role="group" aria-label="촬영지 고르기">
          {places.data?.items.map((p) => (
            <label key={p.id}>
              <input type="checkbox" checked={picked.some((x) => x.id === p.id)} onChange={() => toggle({ id: p.id, name: p.name })} />
              {p.name}
            </label>
          ))}
          {places.data?.items.length === 0 && <span className="muted">이 구·군에는 위치가 확인된 촬영지가 없습니다.</span>}
        </div>
        <p className="muted">
          고른 곳 {picked.length}/10{picked.length > 0 && `: ${picked.map((p) => p.name).join(", ")}`}
        </p>
        <button type="button" className="primary" disabled={picked.length < 2 || plan.isPending} onClick={() => plan.mutate({ ids: picked.map((p) => p.id), fixed: false })}>
          {plan.isPending ? "계산 중…" : "동선 만들기"}
        </button>
        {picked.length < 2 && <span className="muted"> 2곳 이상 골라 주세요.</span>}
      </div>
      {plan.isError && <p className="error">{errorText(plan.error)}</p>}
      {plan.data && (
        <>
          <RouteView route={plan.data} onMove={move} />
          <SaveButton route={plan.data} title={`${plan.data.start.label} 출발 ${plan.data.stops.length}곳`} kind="custom" onSaved={onSaved} />
        </>
      )}
    </div>
  );
}

function AiCourse({ onSaved }: { onSaved: () => void }) {
  const [accepted] = useNotice();
  const [text, setText] = useState("");
  const [start, setStart] = useState("");
  const [budget, setBudget] = useState("");
  const [manual, setManual] = useState<{ genres: string[]; mood_tags: string[]; districts: string[] }>({ genres: [], mood_tags: [], districts: [] });
  const run = useMutation({
    mutationFn: async (body: Omit<AICourseIn, "start" | "budget_h">): Promise<AICourseOut> =>
      endpoints.aiCourse({ ...body, start: await toStart(start), budget_h: budget ? Number(budget) : null }),
  });
  const [options, setOptions] = useState<AICourseOut["options"]>(null);
  const out = run.data;
  if (out?.options && out.options !== options) setOptions(out.options);
  const tooLong = text.length > 200;

  function submit(e: FormEvent) {
    e.preventDefault();
    if (text.trim() && !tooLong && accepted) run.mutate({ preference: text.trim() });
  }

  function toggle(field: keyof typeof manual, v: string) {
    setManual((m) => ({ ...m, [field]: m[field].includes(v) ? m[field].filter((x) => x !== v) : [...m[field], v] }));
  }

  return (
    <div>
      <form className="card filters" onSubmit={submit}>
        <textarea
          className="query"
          aria-label="취향"
          rows={3}
          disabled={!accepted}
          value={text}
          placeholder="예: 서면에서 출발해서 반나절, 바다 보이는 곳 위주로"
          onChange={(e) => setText(e.target.value)}
        />
        <span className={tooLong ? "error" : "muted"}>
          {text.length}/200{tooLong && " · 200자 이내로 줄여 주세요."}
        </span>
        <StartPicker value={start} onChange={setStart} allowText />
        <label>
          시간
          <select aria-label="시간 예산" value={budget} onChange={(e) => setBudget(e.target.value)}>
            <option value="">문장에서 / 4시간</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((h) => (
              <option key={h} value={h}>
                {h}시간
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary" disabled={!accepted || tooLong || !text.trim() || run.isPending}>
          {run.isPending ? "만드는 중…" : "AI 코스 만들기"}
        </button>
      </form>
      {run.isError && <p className="error">{errorText(run.error)}</p>}
      {out?.status === "OUT_OF_SCOPE" && <p className="notice">부산 촬영지 코스와 관련된 취향을 적어 주세요.</p>}
      {out?.status === "INFEASIBLE" && (
        <p className="notice">
          {out.reason === "budget" ? "이 시간 안에는 3곳 이상을 돌 수 없습니다. 시간을 늘려 주세요." : "조건에 맞는 촬영지가 3곳보다 적습니다. 조건을 줄여 주세요."}
        </p>
      )}
      {(out?.status === "FALLBACK" || (options && out?.status !== "OK")) && options && (
        <div className="card filters" aria-label="조건 직접 고르기">
          <p className="notice">AI가 취향을 해석하지 못했습니다. 조건을 직접 골라 주세요.</p>
          {(
            [
              ["genres", "장르"],
              ["mood_tags", "분위기"],
              ["districts", "지역"],
            ] as const
          ).map(([field, label]) => (
            <fieldset key={field}>
              <legend>{label}</legend>
              <div className="checks">
                {options[field].map((v) => (
                  <label key={v}>
                    <input type="checkbox" checked={manual[field].includes(v)} onChange={() => toggle(field, v)} />
                    {v}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          <button type="button" className="primary" disabled={run.isPending} onClick={() => run.mutate({ manual })}>
            이 조건으로 코스 만들기
          </button>
        </div>
      )}
      {out?.notices.map((n) => (
        <p key={n} className="notice">
          {n}
        </p>
      ))}
      {out?.status === "OK" && out.route && out.intro && (
        <>
          <div className="card" aria-label="코스 소개">
            <AiLabel degraded={!out.intro.ai_generated} masked={out.masked} />
            <h2>{out.intro.title}</h2>
            {out.intro.sentences.map((s, i) => (
              <p key={i}>{s}</p>
            ))}
          </div>
          <RouteView route={out.route} reasons={Object.fromEntries(out.reasons.map((r) => [r.location_id, r.text]))} />
          <SaveButton route={out.route} title={out.intro.title} kind="ai" onSaved={onSaved} />
        </>
      )}
    </div>
  );
}

function SavedList({ saved, onRemove }: { saved: SavedCourse[]; onRemove: (key: string) => void }) {
  if (saved.length === 0) return null;
  return (
    <section>
      <h2>
        저장한 코스 {saved.length}/{MAX_SAVED}
      </h2>
      <ul className="list" aria-label="저장한 코스">
        {saved.map((c) => (
          <li key={c.key} className="row">
            <Link className="list-item" to={`/courses/saved/${c.key}`}>
              <strong>{c.title}</strong>
              <span className="muted">
                {c.route.stops.length}곳 · {formatMinutes(c.route.total_min)}
              </span>
            </Link>
            <button type="button" className="button" aria-label={`${c.title} 지우기`} onClick={() => onRemove(c.key)}>
              지우기
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
