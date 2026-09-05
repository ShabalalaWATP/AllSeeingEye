/** Only http(s) links are ever rendered as anchors; anything else from data stays as text. */
export function isHttpUrl(value: string | null | undefined): value is string {
  if (value === null || value === undefined) return false;
  try {
    const protocol = new URL(value).protocol;
    return protocol === 'https:' || protocol === 'http:';
  } catch {
    return false;
  }
}
