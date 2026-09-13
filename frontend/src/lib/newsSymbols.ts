/** A newspaper mask shared by news observations and country reference markers. */
export const NEWS_MASK =
  '<path d="M5 4h16v15a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8h2m0-4v15m4-11h8m-8 4h3m3 0h3m-9 4h3m3 0h3" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>';
export const NEWS_ICON = `data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24">${NEWS_MASK}</svg>`)}`;
