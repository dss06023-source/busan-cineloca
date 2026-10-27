// X-Session-Id: 탭마다 만든 임의 UUID(sessionStorage). 사용자를 식별하지 않는다.
let memoryId: string | null = null;

export function sessionId(): string {
  try {
    let id = window.sessionStorage.getItem("cl.session");
    if (!id) {
      id = crypto.randomUUID();
      window.sessionStorage.setItem("cl.session", id);
    }
    return id;
  } catch {
    memoryId ??= crypto.randomUUID();
    return memoryId;
  }
}
