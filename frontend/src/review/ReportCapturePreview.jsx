import { useEffect, useState } from 'react';
import './report-capture-preview.css';

// Review-only: image bytes stay in the browser and are never uploaded.
export default function ReportCapturePreview() {
  const [image, setImage] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => () => { if (image) URL.revokeObjectURL(image.url); }, [image]);
  const accept = (file) => {
    setError('');
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      setError('PNG·JPG·WebP 이미지 5MB 이하를 선택해 주세요.'); return;
    }
    setImage({ url: URL.createObjectURL(file), name: file.name || '붙여넣은 캡처' });
  };
  useEffect(() => {
    const paste = (event) => {
      const item = Array.from(event.clipboardData?.items || []).find(item => item.kind === 'file' && item.type.startsWith('image/'));
      const file = item?.getAsFile();
      if (!file) return; // Preserve normal text pasting into the description.
      event.preventDefault(); accept(file);
    };
    document.addEventListener('paste', paste);
    return () => document.removeEventListener('paste', paste);
  }, []);
  return <section className="report-capture" aria-label="캡처 미리보기" tabIndex={0}>
    <b>캡처 화면 (선택)</b>
    <p className="report-help"><kbd>Win + Shift + S</kbd>로 범위를 선택한 뒤, 이 미리보기로 돌아와 <kbd>Ctrl + V</kbd>를 누르세요.</p>
    <div className="report-capture-actions"><label>이미지 파일 선택<input type="file" accept="image/png,image/jpeg,image/webp" onChange={event => { const file = event.target.files?.[0]; event.target.value = ''; if (file) accept(file); }} /></label></div>
    <p className="report-help">테스트용 미리보기 · 이미지 1개, 최대 5MB · 서버에 전송되지 않습니다.</p>
    {error && <p role="alert" className="report-help">{error}</p>}
    {image && <figure><img src={image.url} alt="선택한 캡처 미리보기" onError={() => { setImage(null); setError('이미지를 읽을 수 없습니다. 다른 파일을 선택해 주세요.'); }} /><figcaption>{image.name}</figcaption><button type="button" onClick={() => setImage(null)}>캡처 삭제</button></figure>}
  </section>;
}
