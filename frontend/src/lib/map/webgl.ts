/** MapLibre GL JS 6 needs WebGL2; probe once so the page can explain instead of failing. */
export function hasWebGl2(): boolean {
  try {
    const canvas = document.createElement('canvas');
    return canvas.getContext('webgl2') !== null;
  } catch {
    return false;
  }
}
