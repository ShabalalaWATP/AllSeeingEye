/** Recognises a page asking for code that a newer deploy has removed, and reloads it. */

// Chromium, Firefox and Safari word a failed dynamic import differently. Vite's preload
// helper reports a missing stylesheet for the same cause.
const MISSING_CODE =
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Unable to preload CSS/i;

export function isStaleBuildError(error: unknown): boolean {
  return error instanceof Error && MISSING_CODE.test(error.message);
}

export function reloadPage(): void {
  window.location.reload();
}
