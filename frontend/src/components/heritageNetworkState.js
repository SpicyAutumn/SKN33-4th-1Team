// Commit navigation history only after a successful request.
export function createNetworkExplorer(request, initialTarget) {
  let state = { data: null, target: null, history: [], busy: false, error: "" };
  let attempt = null;
  let version = 0;
  let abort;
  const listeners = new Set();
  const publish = (changes) => {
    state = { ...state, ...changes };
    listeners.forEach((listener) => listener());
  };
  const run = async (operation) => {
    abort?.abort();
    abort = new AbortController();
    const current = ++version;
    attempt = operation;
    publish({ busy: true, error: "" });
    try {
      const data = await request(operation.target, { signal: abort.signal });
      if (current !== version) return;
      if (!data?.root && !(data?.requires_selection && data.candidates?.length)) {
        throw new Error("연결 정보의 형식을 확인하지 못했습니다.");
      }
      publish({ data, target: operation.target, history: operation.history, busy: false });
      attempt = null;
    } catch (error) {
      if (current !== version) return;
      publish({ busy: false, error: error.message || "연결 정보를 불러오지 못했습니다." });
    }
  };
  return {
    getSnapshot: () => state,
    subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); },
    open: () => run({ target: initialTarget, history: [] }),
    select: (documentId) => run({ target: { document_id: documentId },
      history: state.target ? [...state.history, state.target] : [] }),
    back: () => state.history.length ? run({ target: state.history.at(-1), history: state.history.slice(0, -1) }) : undefined,
    retry: () => attempt ? run(attempt) : undefined,
    cancel: () => { ++version; abort?.abort(); },
  };
}

export async function fetchHeritageNetwork(target, options) {
  const response = await fetch(`/api/v1/heritage-network?${new URLSearchParams(target)}`, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || "연관 문화유산을 불러오지 못했습니다.");
  return data;
}
