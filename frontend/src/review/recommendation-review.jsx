import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import HeritageNetwork from "../components/HeritageNetwork";
import data from "./recommendation-fixture.json";
import "../styles.css";

const request = async (target) => target.document_id ? data.maps[target.document_id] : data.choice;
function Review() {
  const [question, setQuestion] = useState("");
  return <main style={{ maxWidth: 1000, margin: "auto", padding: 20 }}>
    <h1>추천 근거 확인</h1><p>실제 수집 목록으로 만든 검증 자료입니다. AI 검색과 DB 요청은 실행하지 않습니다.</p>
    <div className="answer-support no-evidence"><HeritageNetwork question="이순신에 대해 알려주세요." request={request} onAsk={setQuestion} recovery /></div>
    <p role="status">선택한 다음 질문: {question || "아직 선택하지 않음"}</p>
  </main>;
}
createRoot(document.getElementById("root")).render(<Review />);
