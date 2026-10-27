// UI-03 작품 목록(FR-101·102): 제목 검색, 장르, 정렬(촬영지 수·개봉연도), 쪽 넘김.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { endpoints, type WorkListParams } from "../api/client";

const PAGE_SIZE = 20;

export function Works() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const genre = params.get("genre") ?? "";
  const sort = params.get("sort") === "year" ? "year" : "locations";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [text, setText] = useState(q);

  const meta = useQuery({ queryKey: ["meta"], queryFn: endpoints.meta, staleTime: Infinity });
  const query: WorkListParams = { q, genre, sort, page };
  const list = useQuery({ queryKey: ["works", query], queryFn: () => endpoints.works(query), placeholderData: keepPreviousData });

  function update(next: Record<string, string | number | undefined>) {
    const merged = { q, genre, sort, page: 1, ...next };
    const out = new URLSearchParams();
    for (const [k, v] of Object.entries(merged)) {
      if (v !== undefined && v !== "" && !(k === "page" && v === 1) && !(k === "sort" && v === "locations")) out.set(k, String(v));
    }
    setParams(out);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    update({ q: text.trim() });
  }

  const total = list.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section className="page">
      <h1>작품</h1>
      <form className="toolbar" role="search" onSubmit={onSubmit}>
        <input aria-label="제목 검색" placeholder="제목 검색" value={text} onChange={(e) => setText(e.target.value)} />
        <button type="submit" className="button">검색</button>
      </form>
      <div className="toolbar">
        <select aria-label="장르" value={genre} onChange={(e) => update({ genre: e.target.value })}>
          <option value="">모든 장르</option>
          {meta.data?.genres.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
        <div className="segmented" role="group" aria-label="정렬">
          <button type="button" aria-pressed={sort === "locations"} onClick={() => update({ sort: "locations" })}>
            촬영지 많은 순
          </button>
          <button type="button" aria-pressed={sort === "year"} onClick={() => update({ sort: "year" })}>
            최신 개봉 순
          </button>
        </div>
      </div>
      {list.isError && <p className="error">{(list.error as Error).message}</p>}
      {list.isLoading && <p className="muted">불러오는 중…</p>}
      {list.data && (
        <>
          <p className="tt-head" aria-hidden="true">
            <span>{total}편</span>
            <span className="tt-num">개봉</span>
            <span className="tt-num">촬영지</span>
          </p>
          {total === 0 && <p>조건에 맞는 작품이 없습니다.</p>}
          <ul className="list" aria-label="작품 목록">
            {list.data.items.map((w) => (
              <li key={w.id}>
                <Link className="list-item tt-row" to={`/works/${w.id}`}>
                  <span className="tt-main">
                    <strong>{w.title}</strong>
                    <span className="muted">{w.genres.join(", ")}</span>
                  </span>
                  <span className="tt-num num" aria-label={w.release_year ? `${w.release_year}년` : "개봉연도 없음"}>
                    {w.release_year ?? "–"}
                  </span>
                  <span className="tt-num" aria-label={`부산 촬영지 ${w.location_count}곳`}>
                    <span className="num">{w.location_count}</span>곳
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <nav className="toolbar" aria-label="쪽">
              <button type="button" className="button" disabled={page <= 1} onClick={() => update({ page: page - 1 })}>
                이전
              </button>
              <span>
                {page} / {pages}
              </span>
              <button type="button" className="button" disabled={page >= pages} onClick={() => update({ page: page + 1 })}>
                다음
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
