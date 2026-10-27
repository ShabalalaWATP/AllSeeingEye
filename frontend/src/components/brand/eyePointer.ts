// Pointer wiring for EvilEyeSurface.tsx: the original React Bits mouse handlers and the
// page-wide following and device hints added for The All Seeing Eye.
// Licence/provenance: EvilEye.tsx and THIRD_PARTY_NOTICES.md.

/** The pupil's current (x, y) and target (tx, ty) offsets, each in -1..1. */
export interface EyeMouse {
  x: number;
  y: number;
  tx: number;
  ty: number;
}

// Added for The All Seeing Eye: device hints for the public hero.
const FINE_POINTER_QUERY = '(hover: hover) and (pointer: fine)';
function hasFinePointer(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(FINE_POINTER_QUERY).matches;
}
export function savesData(): boolean {
  const connection = (navigator as Navigator & { connection?: { saveData?: unknown } }).connection;
  return connection?.saveData === true;
}
const clampUnit = (value: number) => Math.min(1, Math.max(-1, value));

/** Points `mouse` at the pointer over `container` (or the page); returns the cleanup. */
export function followPointer(
  container: HTMLElement,
  mouse: EyeMouse,
  pointerScope: 'surface' | 'page',
): () => void {
  function onMouseMove(e: MouseEvent) {
    const rect = container.getBoundingClientRect();
    mouse.tx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.ty = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
  }
  function onMouseLeave() {
    mouse.tx = 0;
    mouse.ty = 0;
  }
  if (pointerScope === 'page') {
    // Text over the eye must not block it, so listen on the window. Touch and
    // coarse pointers keep a centred pupil; far pointers stop at the eye's edge.
    const onPageMove = (e: MouseEvent) => {
      onMouseMove(e);
      mouse.tx = clampUnit(mouse.tx);
      mouse.ty = clampUnit(mouse.ty);
    };
    const onPageOut = (e: MouseEvent) => {
      if (e.relatedTarget === null) onMouseLeave();
    };
    if (!hasFinePointer()) return () => undefined;
    window.addEventListener('mousemove', onPageMove, { passive: true });
    window.addEventListener('mouseout', onPageOut, { passive: true });
    return () => {
      window.removeEventListener('mousemove', onPageMove);
      window.removeEventListener('mouseout', onPageOut);
    };
  }
  container.addEventListener('mousemove', onMouseMove);
  container.addEventListener('mouseleave', onMouseLeave);
  return () => {
    container.removeEventListener('mousemove', onMouseMove);
    container.removeEventListener('mouseleave', onMouseLeave);
  };
}
