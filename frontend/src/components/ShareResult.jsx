import { useEffect, useState } from "react";
import "./ShareResult.css";

export default function ShareResult({ result, request }) {
  const [url, setUrl] = useState(result.share_path ? new URL(result.share_path, window.location.origin).href : "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const resultId = result.search_result_id || result.search_record_id || result.id;
  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(() => setMessage(""), 2000);
    return () => window.clearTimeout(timer);
  }, [message]);
  const share = async () => {
    setBusy(true); setMessage("");
    try {
      let link = url;
      if (!link) {
        if (!resultId) throw new Error("공유할 검색 결과를 찾을 수 없습니다.");
        const { share_path: path } = await request(`searches/${resultId}/share`, { method: "POST" });
        link = new URL(path, window.location.origin).href;
        setUrl(link);
      }
      await navigator.clipboard.writeText(link);
      setMessage("복사되었습니다");
    } catch {
      setMessage("복사하지 못했습니다. 다시 시도해 주세요.");
    } finally { setBusy(false); }
  };
  return <section className="search-share" aria-label="답변 공유">
    <button type="button" className="outline search-share-button" onClick={share} disabled={busy}
      title="링크를 가진 누구나 이 질문과 답변, 출처를 볼 수 있어요.">
      {busy ? "복사 중…" : "공유하기"}
    </button>
    <p className="search-share-toast" role="status" aria-live="polite" aria-atomic="true">{message}</p>
  </section>;
}
