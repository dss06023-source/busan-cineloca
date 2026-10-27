// 아직 만들지 않은 화면 자리(WP-08~11에서 채운다).
export function Placeholder({ title, wp }: { title: string; wp: string }) {
  return (
    <section className="page">
      <h1>{title}</h1>
      <p className="muted">준비 중입니다({wp}).</p>
    </section>
  );
}
