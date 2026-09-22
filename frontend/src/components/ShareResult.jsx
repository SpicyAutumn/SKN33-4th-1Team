import { useState } from "react";
import "./ShareResult.css";

export default function ShareResult({ result, request }) {
  const [url, setUrl] = useState(result.share_path ? new URL(result.share_path, window.location.origin).href : "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const share = async () => {
    setBusy(true); setMessage("");
    try {
      let link = url;
      if (!link) {
        const { share_path: path } = await request(`searches/${result.search_result_id}/share`, { method: "POST" });
        link = new URL(path, window.location.origin).href;
        setUrl(link);
      }
      try {
        await navigator.clipboard.writeText(link);
        setMessage("공유 링크를 복사했어요.");
      } catch {
        setMessage("아래 주소를 선택해서 복사해 주세요.");
      }
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  };
  return <section className="search-share" aria-label="답변 공유">
    <div><button type="button" className="outline" onClick={share} disabled={busy}>
      {busy ? "링크 준비 중…" : "링크 공유"}
    </button><span>{result.shared ? "공유된 답변입니다." : "공유하면 링크를 가진 누구나 이 질문과 답변, 출처를 볼 수 있어요."}</span></div>
    {url && <label>공유 주소<input aria-label="공유 주소" readOnly value={url} onFocus={(event) => event.target.select()} /></label>}
    <p role="status">{message}</p>
  </section>;
}
