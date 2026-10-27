// UI-11 검수 큐(FR-608~610): AI·규칙 제안을 고치거나 승인·거절하고, 촬영지 속성을 같은 화면에서 편집한다.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router";
import { endpoints, type LocationAttrsIn, type ReviewItem } from "../../api/client";
import { isUnauthorized } from "./AdminLayout";

export function parseTags(text: string): string[] {
  return [...new Set(text.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean))];
}

function ReviewCard({ item }: { item: ReviewItem }) {
  const qc = useQueryClient();
  const proposal = item.proposal ?? {};
  const [tags, setTags] = useState(Array.isArray(proposal.tags) ? (proposal.tags as string[]).join(", ") : "");
  const [kmdb, setKmdb] = useState(typeof proposal.kmdb_id === "string" ? proposal.kmdb_id : "");
  const decide = useMutation({
    mutationFn: endpoints.decide,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-reviews"] }),
  });
  const edit = item.kind === "tag" ? { tags: parseTags(tags) } : { kmdb_id: kmdb.trim() };
  return (
    <li className="card" aria-label={`검수 ${item.id}`}>
      <p>
        <strong>{item.kind === "tag" ? "태그" : "작품 매칭"}</strong> · {item.target_label ?? `${item.target_type} #${item.target_id}`}
        <span className="muted">
          {" "}
          · 제안 {item.proposer === "ai" ? `AI(${item.model ?? "?"})` : "규칙"}
          {item.score != null && ` · 점수 ${item.score.toFixed(2)}`}
        </span>
      </p>
      {item.kind === "tag" ? (
        <label>
          태그(쉼표로 구분)
          <input value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>
      ) : (
        <>
          <p className="muted">{JSON.stringify(proposal)}</p>
          <label>
            KMDb ID
            <input value={kmdb} onChange={(e) => setKmdb(e.target.value)} />
          </label>
        </>
      )}
      <p>
        <button type="button" className="primary" disabled={decide.isPending} onClick={() => decide.mutate({ id: item.id, action: "approve", edit })}>
          승인
        </button>{" "}
        <button type="button" className="button" disabled={decide.isPending} onClick={() => decide.mutate({ id: item.id, action: "reject" })}>
          거절
        </button>
      </p>
      {decide.isError && <p className="error">{(decide.error as Error).message}</p>}
    </li>
  );
}

function LocationEditor() {
  const [id, setId] = useState("");
  const [caution, setCaution] = useState("");
  const [note, setNote] = useState("");
  const [radius, setRadius] = useState("");
  const [excluded, setExcluded] = useState<"" | "true" | "false">("");
  const save = useMutation({
    mutationFn: () =>
      endpoints.updateLocation(Number(id), {
        caution: (caution || null) as LocationAttrsIn["caution"],
        safety_note: note || null,
        cert_radius_m: radius ? Number(radius) : null,
        cert_excluded: excluded ? excluded === "true" : null,
      }),
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    if (Number(id) > 0) save.mutate();
  }
  return (
    <form className="card filters" onSubmit={submit} aria-label="촬영지 속성 편집">
      <h2>촬영지 속성 편집</h2>
      <p className="muted">비운 칸은 바꾸지 않습니다. 동기화해도 이 값은 덮어쓰지 않습니다.</p>
      <label>
        촬영지 ID
        <input inputMode="numeric" value={id} onChange={(e) => setId(e.target.value.replace(/\D/g, ""))} />
      </label>
      <label>
        주의 구분
        <select value={caution} onChange={(e) => setCaution(e.target.value)}>
          <option value="">그대로</option>
          <option value="none">없음</option>
          <option value="private">사유지</option>
          <option value="residential">주거지</option>
          <option value="school">학교</option>
        </select>
      </label>
      <label>
        안전 안내
        <input maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <label>
        인증 반경(50~300m)
        <input type="number" min={50} max={300} value={radius} onChange={(e) => setRadius(e.target.value)} />
      </label>
      <label>
        인증 제외
        <select value={excluded} onChange={(e) => setExcluded(e.target.value as "" | "true" | "false")}>
          <option value="">그대로</option>
          <option value="true">제외</option>
          <option value="false">인증 가능</option>
        </select>
      </label>
      <button type="submit" className="primary" disabled={!id || save.isPending}>
        저장
      </button>
      {save.isSuccess && (
        <p className="notice">
          저장했습니다: {save.data.name} · {save.data.caution} · 반경 {save.data.cert_radius_m}m{save.data.cert_excluded && " · 인증 제외"}
        </p>
      )}
      {save.isError && <p className="error">{(save.error as Error).message}</p>}
    </form>
  );
}

export function AdminReviews() {
  const [kind, setKind] = useState<"" | "tag" | "match">("");
  const q = useQuery({ queryKey: ["admin-reviews", kind], queryFn: () => endpoints.reviews(kind || undefined) });
  if (isUnauthorized(q.error)) return <Navigate to="/admin/login" replace />;
  return (
    <section>
      <h1>검수</h1>
      <div className="toolbar">
        <select aria-label="종류" value={kind} onChange={(e) => setKind(e.target.value as "" | "tag" | "match")}>
          <option value="">전체</option>
          <option value="tag">태그</option>
          <option value="match">작품 매칭</option>
        </select>
        <span className="muted"> 대기 {q.data?.items.length ?? 0}건</span>
      </div>
      {q.isError && <p className="error">{(q.error as Error).message}</p>}
      {q.data?.items.length === 0 && <p className="muted">검수할 항목이 없습니다.</p>}
      <ul className="list" aria-label="검수 목록">
        {q.data?.items.map((i) => <ReviewCard key={i.id} item={i} />)}
      </ul>
      <LocationEditor />
    </section>
  );
}
