// Development only. Catalog-derived fixture; no external API or database writes.
import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import HeritageNetwork from "../components/HeritageNetwork";
import data from "./network-fixture.json";
import "../styles.css";

function Review() {
  const failNext = useRef(false);
  const [calls, setCalls] = useState([]);
  const [answerKey, setAnswerKey] = useState(1);
  const [request] = useState(() => async (target) => {
    const label = target.document_id || target.question;
    setCalls((old) => [...old, label]);
    if (failNext.current) { failNext.current = false; throw new Error("검증용 조회 실패입니다. 기존 답변과 탐색 기록은 유지됩니다."); }
    if (target.question) return data.choice;
    return data.maps[target.document_id] || { root: { title: "검증용 하위 항목", document_id: target.document_id, fields: [] }, branches: [] };
  });
  return <main style={{ maxWidth: 1000, margin: "auto", padding: 20 }}>
    <h1>연관 문화유산 탐색 검증</h1><p>실제 목록 기반 자료 · 요청 실패는 모의 처리 · AI/DB 미사용</p>
    <button onClick={() => { failNext.current = true; }}>다음 조회 한 번 실패</button>{" "}
    <button onClick={() => setAnswerKey((old) => old + 1)}>새 답변으로 초기화</button>
    <article><h2>기존 답변</h2><p>경복궁과 창덕궁은 조선 시대의 궁궐입니다. 이 문장은 탐색 오류가 발생해도 유지됩니다.</p></article>
    <HeritageNetwork answerKey={answerKey} question="경복궁과 창덕궁의 차이" request={request} />
    <details><summary>요청 기록</summary><ol>{calls.map((call, index) => <li key={index}>{call}</li>)}</ol></details>
  </main>;
}
createRoot(document.getElementById("root")).render(<Review />);
