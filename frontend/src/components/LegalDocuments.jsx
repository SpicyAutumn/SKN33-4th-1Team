import { useEffect, useRef, useState } from 'react';
import './LegalDocuments.css';

const documents = { terms: '이용약관', privacy: '개인정보 처리방침' };

export default function LegalDocuments() {
  const [selected, setSelected] = useState(null);
  const dialog = useRef(null);
  const opener = useRef(null);
  const frameCleanup = useRef(() => {});
  const close = () => setSelected(null);

  useEffect(() => {
    if (!selected) return;
    const element = dialog.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element.showModal();
    return () => {
      frameCleanup.current();
      element.close();
      document.body.style.overflow = overflow;
      opener.current?.focus();
    };
  }, [Boolean(selected)]);

  const prepareFrame = (event) => {
    frameCleanup.current();
    const doc = event.currentTarget.contentDocument;
    if (!doc) return;
    doc.querySelectorAll('nav, footer').forEach(element => { element.style.display = 'none'; });
    const onKey = event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); }
    };
    const onLink = event => {
      const link = event.target.closest('a');
      if (!link) return;
      const kind = Object.keys(documents).find(key => new URL(link.href).pathname === `/legal/${key}.html`);
      if (kind) { event.preventDefault(); setSelected(kind); }
    };
    doc.addEventListener('keydown', onKey);
    doc.addEventListener('click', onLink);
    frameCleanup.current = () => {
      doc.removeEventListener('keydown', onKey);
      doc.removeEventListener('click', onLink);
    };
  };

  return <>
    <nav aria-label="서비스 정책">{Object.entries(documents).map(([key, title]) =>
      <a key={key} href={`/legal/${key}.html`} onClick={event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault(); opener.current = event.currentTarget; setSelected(key);
      }}>{title}</a>)}</nav>
    <dialog className="legal-document-dialog" ref={dialog} aria-labelledby="legal-document-title" onCancel={event => { event.preventDefault(); close(); }}>
      <header><h2 id="legal-document-title">{documents[selected]}</h2><button type="button" autoFocus onClick={close} aria-label="문서 닫기">닫기 ×</button></header>
      {selected && <iframe key={selected} src={`/legal/${selected}.html`} title={documents[selected]} sandbox="allow-same-origin allow-popups" onLoad={prepareFrame} />}
    </dialog>
  </>;
}
