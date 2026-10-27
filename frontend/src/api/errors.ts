// ERR 코드별 화면 문구(SDD 8장). 문구는 이 파일 한 곳에서만 고친다.
export const ERROR_MESSAGES: Record<string, string> = {
  "ERR-001": "입력 값을 확인해 주세요.",
  "ERR-002": "이용 안내를 먼저 확인해 주세요.",
  "ERR-009": "이 촬영지는 방문 인증을 할 수 없습니다.",
  "ERR-011": "요청이 많습니다. 잠시 후 다시 시도해 주세요.",
  "ERR-012": "관리자 인증에 실패했습니다.",
  "ERR-015": "서버에 잠시 연결할 수 없습니다. 저장된 스탬프북과 코스는 계속 볼 수 있습니다.",
  "ERR-016": "일시적인 오류가 발생했습니다.",
  "HTTP-404": "찾는 정보가 없습니다.",
};

export function messageFor(code: string | undefined): string {
  return (code && ERROR_MESSAGES[code]) || "요청을 처리하지 못했습니다.";
}
