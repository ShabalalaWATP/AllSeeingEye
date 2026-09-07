/** Browser selections use UTF-16; the frozen evidence API uses Unicode code points. */
export function selectedExcerpt(text: string, start: number, end: number) {
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    start >= end ||
    end > text.length
  )
    return null;
  const splitsPair = (offset: number) =>
    offset > 0 &&
    offset < text.length &&
    /[\uD800-\uDBFF]/.test(text[offset - 1] ?? '') &&
    /[\uDC00-\uDFFF]/.test(text[offset] ?? '');
  if (splitsPair(start) || splitsPair(end)) return null;
  const excerpt = text.slice(start, end);
  if (!excerpt.trim() || Array.from(excerpt).length > 1200) return null;
  return {
    start: Array.from(text.slice(0, start)).length,
    end: Array.from(text.slice(0, end)).length,
    text: excerpt,
  };
}

/** Textareas normalise CRLF and CR to LF; retain positions in the original captured field. */
export function selectedTextareaExcerpt(text: string, start: number, end: number) {
  const boundaries = [0];
  for (let position = 0; position < text.length; position += 1) {
    if (text[position] === '\r' && text[position + 1] === '\n') position += 1;
    boundaries.push(position + 1);
  }
  const rawStart = boundaries[start];
  const rawEnd = boundaries[end];
  if (rawStart === undefined || rawEnd === undefined) return null;
  return selectedExcerpt(text, rawStart, rawEnd);
}
