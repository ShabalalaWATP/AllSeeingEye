/** Update one document-head value and restore its previous state when its route leaves. */
export function setDocumentMeta(
  key: string,
  content: string,
  attribute: 'name' | 'property' = 'name',
): () => void {
  const existing = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`);
  const node = existing ?? document.createElement('meta');
  const previous = node.getAttribute('content');
  node.setAttribute(attribute, key);
  node.content = content;
  if (existing === null) document.head.append(node);
  return () => {
    if (existing === null) node.remove();
    else if (previous === null) node.removeAttribute('content');
    else node.content = previous;
  };
}

export function setCanonicalUrl(url: string): () => void {
  const existing = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  const node = existing ?? document.createElement('link');
  const previous = node.getAttribute('href');
  node.rel = 'canonical';
  node.href = url;
  if (existing === null) document.head.append(node);
  return () => {
    if (existing === null) node.remove();
    else if (previous === null) node.removeAttribute('href');
    else node.setAttribute('href', previous);
  };
}
