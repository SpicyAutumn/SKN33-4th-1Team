// Return exact slices: concatenation must always reproduce the source text.
// Existing formatting and ambiguous punctuation are deliberately left alone.
export function displayParagraphs(text) {
  if (typeof text !== 'string' || text.length < 240 || /[\r\n]/.test(text)
    || /https?:\/\/|["“”「」『』]/.test(text)) return [text];
  const endings = [...text.matchAll(/[가-힣](?:다|요)[.!?][ \t]+(?=[가-힣A-Za-z0-9])/g)];
  const chunks = [];
  let start = 0;
  let sentences = 0;
  for (const ending of endings) {
    sentences += 1;
    const end = ending.index + ending[0].length;
    if (sentences >= 2 && end - start >= 150 && text.length - end >= 60) {
      chunks.push(text.slice(start, end)); start = end; sentences = 0;
    }
  }
  chunks.push(text.slice(start));
  return chunks;
}
