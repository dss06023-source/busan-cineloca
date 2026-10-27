"""KmdbCsvCatalog(DATA-04): KMDb 오픈자료 '영화기본정보' CSV를 읽는 로컬 어댑터.

KMDb API 키가 승인되기 전까지 작품 매칭 후보(제목 + 연도 → kmdb_id, BR-11)와 상세(줄거리·키워드·링크)를 여기서 얻는다.
원본 CSV는 저장소에 넣지 않고 KMDB_CSV_PATH로 가리킨다. 저장 범위는 PolicyGuard가 DATA-04 정책으로 정한다(TBD-01).

파일 형식(2026-10-27 받은 파일로 확인): CP949, 헤더는 25칸인데 데이터 행은 26칸이다. 헤더의 '출연' 뒤에
'출연'이 한 번 더 있어 이름으로 읽으면 한 칸씩 밀리므로 위치로 읽는다. 값이 없으면 문자열 'null'이다.
같은 ID가 두 번 나오는 행이 약 1천 건 있어 처음 것만 쓴다.
"""

import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from app.data.adapters.errors import AdapterError, ResponseFormatError
from app.data.models import MovieInfo
from app.data.text import normalize

SOURCE_ID = "DATA-04"
# 데이터 행 26칸의 실제 순서(14는 12와 같은 출연 목록)
COLUMNS = (
    "id_kind", "id_no", "title", "title_en", "title_org", "kind", "usage", "genres", "nations", "prdt_year",
    "companies", "directors", "actors", "writers", "actors_dup", "audited", "audit_date", "audit_no", "grade",
    "release_date", "running_min", "keywords", "plot", "kmdb_url", "created_at", "updated_at",
)  # fmt: skip
HEADER_FIRST = "영화등록번호ID"
HEADER_LEN = 25
# KMDBURL 칸이 비어 있어 KMDb 상세 페이지 주소 형식으로 만든다
DETAIL_URL = "https://www.kmdb.or.kr/db/kor/detail/movie/{kind}/{no}"
_ROLE = re.compile(r"\s*\([^)]*\)\s*$")


@dataclass(frozen=True)
class KmdbMovie:
    kmdb_id: str  # 'K14687' = 영화등록번호ID + NO(KMDb API의 movieId + movieSeq)
    title: str
    title_en: str | None
    title_org: str | None
    kind: str | None  # 극영화·애니메이션·다큐멘터리 등
    genres: tuple[str, ...]
    nations: tuple[str, ...]
    prdt_year: int | None
    directors: tuple[str, ...]
    actors: tuple[str, ...]  # 배역 괄호는 뺀 이름
    keywords: tuple[str, ...]
    plot: str | None
    release_date: str | None  # YYYYMMDD
    link: str


def _val(v: str) -> str | None:
    v = v.strip()
    return None if v in ("", "null") else v


def _list(v: str, strip_role: bool = False) -> tuple[str, ...]:
    items = (_ROLE.sub("", s).strip() if strip_role else s.strip() for s in (_val(v) or "").split(","))
    return tuple(dict.fromkeys(s for s in items if s))


def parse_row(row: list[str]) -> KmdbMovie:
    if len(row) != len(COLUMNS):
        raise ResponseFormatError(f"kmdb_csv: row has {len(row)} columns")
    c = dict(zip(COLUMNS, row, strict=True))
    year = _val(c["prdt_year"])
    plot = _val(c["plot"])
    return KmdbMovie(
        kmdb_id=f"{c['id_kind']}{c['id_no']}",
        title=c["title"].strip(),
        title_en=_val(c["title_en"]),
        title_org=_val(c["title_org"]),
        kind=_val(c["kind"]),
        genres=_list(c["genres"]),
        nations=_list(c["nations"]),
        prdt_year=int(year) if year and year.isdigit() else None,
        directors=_list(c["directors"]),
        actors=_list(c["actors"], strip_role=True),
        keywords=_list(c["keywords"]),
        plot=plot.replace("\r\n", "\n") if plot else None,
        release_date=_val(c["release_date"]),
        link=_val(c["kmdb_url"]) or DETAIL_URL.format(kind=c["id_kind"], no=c["id_no"]),
    )


def read_csv(path: Path | str, encoding: str = "cp949") -> Iterator[KmdbMovie]:
    with open(path, encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header[0].lstrip("﻿") != HEADER_FIRST or len(header) != HEADER_LEN:
            raise ResponseFormatError("kmdb_csv: unexpected header")
        for row in reader:
            if row:
                yield parse_row(row)


class KmdbCsvCatalog:
    """메모리 색인. 배치가 한 번 읽어 매칭 후보와 상세를 꺼낸다."""

    def __init__(self, movies: Iterable[KmdbMovie]):
        self.by_id: dict[str, KmdbMovie] = {}
        self._by_title: dict[str, list[str]] = defaultdict(list)
        self._by_head: dict[str, set[str]] = defaultdict(set)  # 정규화 제목 앞 두 글자 → 제목
        for m in movies:
            if m.kmdb_id in self.by_id:
                continue
            self.by_id[m.kmdb_id] = m
            for t in {normalize(t) for t in (m.title, m.title_en, m.title_org) if t}:
                if t:
                    self._by_title[t].append(m.kmdb_id)
                    self._by_head[t[:2]].add(t)

    @classmethod
    def load(cls, path: Path | str, encoding: str = "cp949") -> "KmdbCsvCatalog":
        return cls(read_csv(path, encoding))

    def __len__(self) -> int:
        return len(self.by_id)

    def candidates(self, title: str, year: int | None = None, limit: int = 3) -> list[KmdbMovie]:
        """제목이 같은 작품을 먼저, 없으면 한쪽이 다른 쪽의 앞부분인 제목('범죄도시'·'범죄도시2')을 찾아
        연도가 가까운 순으로 돌려준다. 점수와 자동 연결·검수 판단은 WorkMatcher가 한다."""
        q = normalize(title)
        if not q:
            return []
        exact = set(self._by_title.get(q, ()))
        near = {
            i
            for t in self._by_head.get(q[:2], ())
            if t != q and (t.startswith(q) or q.startswith(t))
            for i in self._by_title[t]
        } - exact

        def rank(i: str) -> tuple:
            m = self.by_id[i]
            gap = abs(m.prdt_year - year) if (year and m.prdt_year) else 99
            return (i not in exact, gap, i)

        return [self.by_id[i] for i in sorted(exact | near, key=rank)[:limit]]

    async def detail(self, kmdb_id: str) -> MovieInfo:
        """MovieInfoProvider(ArchiveService). 이미지·예고편 칸은 CSV에 없다."""
        m = self.by_id.get(kmdb_id)
        if m is None:
            raise AdapterError(f"kmdb_csv: unknown id {kmdb_id}")
        return MovieInfo(source_id=SOURCE_ID, plot=m.plot, keywords=list(m.keywords), link=m.link)
