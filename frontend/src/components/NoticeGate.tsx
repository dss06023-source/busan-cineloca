// 첫 방문 이용 안내(FR-701). 확인 전에는 AI 입력을 막고, 확인하면 cl.notice에 버전을 적는다.
import { useEffect, type ReactNode } from "react";
import { NOTICE_REQUIRED_EVENT } from "../api/client";
import { NOTICE_VERSION } from "../config";
import { KEYS, useStored } from "../lib/storage";

export function useNotice(): [boolean, () => void, () => void] {
  const [seen, setSeen] = useStored<string | null>(KEYS.notice, null);
  return [seen === NOTICE_VERSION, () => setSeen(NOTICE_VERSION), () => setSeen(null)];
}

export function NoticeGate({ children }: { children: ReactNode }) {
  const [accepted, accept, reset] = useNotice();

  useEffect(() => {
    window.addEventListener(NOTICE_REQUIRED_EVENT, reset);
    return () => window.removeEventListener(NOTICE_REQUIRED_EVENT, reset);
  }, [reset]);

  return (
    <>
      {children}
      {/* 관리자 화면은 사용자 안내 대상이 아니다(UI-10~12) */}
      {!accepted && !window.location.pathname.startsWith("/admin") && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="notice-title">
          <div className="modal">
            <h2 id="notice-title">이용 안내</h2>
            <ul>
              <li>AI 탐색·코스·작품 소개에 입력한 문장은 외부 AI 서비스(Google Gemini)로 보내질 수 있습니다. 전화번호 등 개인정보는 가린 뒤 보냅니다.</li>
              <li>현재 위치는 검색과 방문 인증에만 쓰고 서버에 저장하지 않습니다.</li>
              <li>스탬프·저장 코스는 이 브라우저에만 저장됩니다.</li>
              <li>AI가 만든 문장에는 'AI 생성' 표시가 붙고, 틀릴 수 있습니다.</li>
            </ul>
            <button type="button" className="primary" onClick={accept}>
              확인했습니다
            </button>
          </div>
        </div>
      )}
    </>
  );
}
