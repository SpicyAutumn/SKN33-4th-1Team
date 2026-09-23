import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { createNetworkExplorer, fetchHeritageNetwork } from "./heritageNetworkState";
import "./HeritageNetwork.css";

function SourceLink({ url }) {
  if (!/^https?:\/\//i.test(url || "")) return null;
  return <a href={url} target="_blank" rel="noopener noreferrer">백과사전 원문 ↗</a>;
}

export default function HeritageNetwork(props) {
  // A new answer gets a fresh explorer, including when the same question is regenerated.
  return <Explorer key={props.answerKey} {...props} />;
}

function Explorer({ question, onAsk, recovery = false, citations = [], request = fetchHeritageNetwork }) {
  const documentIds = [...new Set(citations.map((citation) => citation.document_id)
    .filter((id) => /^aks:[A-Za-z0-9_-]{1,64}$/.test(id || "")))].slice(0, 10).join(",");
  const explorer = useMemo(() => createNetworkExplorer(request, { question, document_ids: documentIds }), [request, question, documentIds]);
  const state = useSyncExternalStore(explorer.subscribe, explorer.getSnapshot, explorer.getSnapshot);

  const [showAll, setShowAll] = useState(false);

  useEffect(() => { explorer.open(); return () => explorer.cancel(); }, [explorer]);
  const root = state.data?.root;
  return <section className="heritage-network" aria-label={recovery ? "다른 질문으로 찾아보기" : "함께 알아보기"}>
    <div className="heritage-network-heading"><h2>{recovery ? "다른 질문으로 찾아보기" : "함께 알아보기"}</h2></div>
    <p className="heritage-network-note">제목·주제어의 연결 근거가 있는 항목입니다. 답변 근거가 충분한지는 다시 검색해야 확인할 수 있어요.</p>
    <div>
      {(state.history.length > 0 || state.busy) && <div className="heritage-network-toolbar">
        {state.history.length > 0 && <button type="button" disabled={state.busy} onClick={explorer.back}>← 이전 탐색</button>}
        {state.busy && <span role="status">연결 정보를 불러오고 있어요.</span>}
      </div>}
      {state.error && <div className="heritage-network-error" role="alert"><p>{state.error}</p><button type="button" onClick={explorer.retry} disabled={state.busy}>실패한 요청 다시 시도</button></div>}
      {state.data?.requires_selection && <div><h3>탐색할 중심 대상을 선택해 주세요</h3>
        <p>질문 또는 참고 자료에서 여러 대상을 찾았습니다.</p>
        {state.data.candidate_count > state.data.candidates.length && <p>후보 중 앞의 {state.data.candidates.length}개를 표시합니다. 원하는 대상이 없다면 질문을 더 구체적으로 입력해 주세요.</p>}
        <ul>{state.data.candidates.map((candidate) => <li key={candidate.document_id}><button type="button" disabled={state.busy} onClick={() => explorer.select(candidate.document_id)}>{candidate.title}<small>{[candidate.field, candidate.item_type].filter(Boolean).join(" · ")}</small>{candidate.keywords?.length > 0 && <small>주제어: {candidate.keywords.join(", ")}</small>}</button></li>)}</ul></div>}
      {root && <div aria-busy={state.busy}><div className="heritage-network-root"><h3>{root.title}</h3><SourceLink url={root.source_url} /></div>
        <p className="heritage-network-note">{root.fields?.map(([label, value]) => `${label}: ${value}`).join(" · ")}</p>
        {!state.data.branches?.length && <p>현재 목록에서 연결 근거가 충분한 추천 항목을 찾지 못했습니다.</p>}
        <div className="heritage-network-branches">{(showAll ? state.data.branches || [] : (state.data.branches || []).slice(0, 3)).map((branch) => <section key={branch.title}><h4>{branch.title}</h4>{branch.note && <p className="heritage-network-note">{branch.note}</p>}<ul>{(showAll ? branch.nodes : branch.nodes.slice(0, 3)).map((node) => <li key={node.document_id}><button type="button" disabled={state.busy} onClick={() => onAsk ? onAsk(`${node.title}에 대해 알려주세요.`) : explorer.select(node.document_id)}>{node.title}<small>{node.item_type}</small></button>{node.reason && <small className="heritage-network-reason">{node.reason}</small>}</li>)}</ul></section>)}</div>
        {(state.data.branches?.length > 3 || state.data.branches?.some((branch) => branch.nodes.length > 3)) && <button type="button" aria-expanded={showAll} onClick={() => setShowAll(!showAll)}>{showAll ? '간단히 보기' : '연관 항목 더 보기'}</button>}</div>}
    </div>
  </section>;
}
