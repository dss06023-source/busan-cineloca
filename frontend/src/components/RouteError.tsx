// 화면을 그리다 오류가 나면 react-router 기본(영문) 화면 대신 이 안내를 보여 준다.
import { isRouteErrorResponse, Link, useRouteError } from "react-router";

export function RouteError() {
  const e = useRouteError();
  if (isRouteErrorResponse(e) && e.status === 404) return <NotFound />;
  return (
    <section className="page" role="alert">
      <h1>화면을 표시하지 못했습니다</h1>
      <p className="muted">잠시 뒤 다시 시도해 주세요. 계속되면 처음 화면에서 다시 시작해 주세요.</p>
      <div className="row">
        <button type="button" className="button" onClick={() => window.location.reload()}>
          다시 시도
        </button>
        <Link className="button" to="/">
          지도 홈으로
        </Link>
      </div>
    </section>
  );
}

export function NotFound() {
  return (
    <section className="page">
      <h1>페이지를 찾을 수 없습니다</h1>
      <p className="muted">주소가 바뀌었거나 없는 화면입니다.</p>
      <Link className="button" to="/">
        지도 홈으로
      </Link>
    </section>
  );
}
