export const CSRF_COOKIE = 'ase_csrf';
export const CSRF_HEADER = 'X-CSRF-Token';

/** Reads one cookie value by name from document.cookie, or null when absent. */
export function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) {
      return decodeURIComponent(trimmed.slice(prefix.length));
    }
  }
  return null;
}

/** Headers for the cookie-bearing auth endpoints (refresh and logout). */
export function csrfHeaders(): Record<string, string> {
  const token = readCookie(CSRF_COOKIE);
  return token === null ? {} : { [CSRF_HEADER]: token };
}
