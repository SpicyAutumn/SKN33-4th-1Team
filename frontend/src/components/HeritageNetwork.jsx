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

function Explorer({ question, onAsk, citations = [], request = fetchHeritageNetwork }) {
  const documentIds = [...new Set(citations.map((citation) => citation.document_id)
    .filter((id) => /^aks:[A-Za-z0-9_-]{1,64}$/.test(id || "")))].slice(0, 10).join(",");
  const explorer = useMemo(() => createNetworkExplorer(request, { question, document_ids: documentIds }), [request, question, documentIds]);
  const state = useSyncExternalStore(explorer.subscribe, explorer.getSnapshot, explorer.getSnapshot);
  const [expanded, setExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const [wide, setWide] = useState(false);
  useEffect(() => { explorer.open(); return () => explorer.cancel(); }, [explorer]);
  const root = state.data?.root;
  return <section className={`heritage-network${wide ? " is-wide" : ""}`} aria-label="함께 알아보기">
    <div className="heritage-network-heading"><div><h2>함께 알아보기</h2><p>이름·분류·지역 정보가 연결되는 다른 유산을 찾아보세요.</p></div>
      <button type="button" disabled={state.busy} aria-expanded={expanded} onClick={() => {
        setExpanded(!expanded);
        if (!expanded && !state.data) explorer.open();
      }}>{expanded ? "접기" : "탐색 열기"}</button></div>
    {expanded && <div><button type="button" aria-pressed={wide} onClick={() => setWide(!wide)}>{wide ? "작게 보기" : "크게 보기"}</button>
      <p className="heritage-network-note">문화유산 목록을 기준으로 안내합니다. 실제 역사적 관계나 방문 가능 여부는 원문에서 확인해 주세요.</p>
      <div className="heritage-network-toolbar"><button type="button" disabled={state.busy || !state.history.length} onClick={explorer.back}>← 이전 탐색</button>
        {state.busy && <span role="status">연결 정보를 불러오고 있어요.</span>}</div>
      {state.error && <div className="heritage-network-error" role="alert"><p>{state.error}</p><button type="button" onClick={explorer.retry} disabled={state.busy}>실패한 요청 다시 시도</button></div>}
      {state.data?.requires_selection && <div><h3>탐색할 중심 대상을 선택해 주세요</h3>
        <p>질문 또는 참고 자료에서 여러 대상을 찾았습니다.</p>
        {state.data.candidate_count > state.data.candidates.length && <p>후보 중 앞의 {state.data.candidates.length}개를 표시합니다. 원하는 대상이 없다면 질문을 더 구체적으로 입력해 주세요.</p>}
        <ul>{state.data.candidates.map((candidate) => <li key={candidate.document_id}><button type="button" disabled={state.busy} onClick={() => explorer.select(candidate.document_id)}>{candidate.title}<small>{[candidate.field, candidate.item_type].filter(Boolean).join(" · ")}</small></button></li>)}</ul></div>}
      {root && <div aria-busy={state.busy}><div className="heritage-network-root"><h3>{root.title}</h3><p>{(root.fields || []).map(([label, value]) => `${label}: ${value}`).join(" · ")}</p><SourceLink url={root.source_url} /></div>
        {!state.data.branches?.length && <p>현재 목록에서 연결할 항목을 찾지 못했습니다.</p>}
        <div className="heritage-network-branches">{(showAll ? state.data.branches || [] : (state.data.branches || []).slice(0, 3)).map((branch) => <section key={branch.title}><h4>{branch.title}</h4><details><summary>연결 기준</summary><p>{branch.note}</p></details><ul>{(showAll ? branch.nodes : branch.nodes.slice(0, 3)).map((node) => <li key={node.document_id}><button type="button" disabled={state.busy} onClick={() => onAsk ? onAsk(`${node.title}의 위치와 특징은 무엇인가요?`) : explorer.select(node.document_id)}>{node.title}<small>{onAsk ? "질문으로 알아보기 →" : node.reason}</small></button>{onAsk && <button type="button" className="network-explore" aria-label={`${node.title} 연관 탐색`} disabled={state.busy} onClick={() => explorer.select(node.document_id)}>연관 탐색</button>}</li>)}</ul></section>)}</div>
        {(state.data.branches?.length > 3 || state.data.branches?.some((branch) => branch.nodes.length > 3)) && <button type="button" aria-expanded={showAll} onClick={() => setShowAll(!showAll)}>{showAll ? '간단히 보기' : '연관 항목 더 보기'}</button>}</div>}
    </div>}
  </section>;
}
