import { useEffect } from 'react';

import { useShellStore } from '@/stores/shell';

/** Ctrl or Cmd K, outside any open dialog and not already handled by the page. */
export function isPaletteShortcut(event: KeyboardEvent): boolean {
  const inDialog = event.target instanceof Element && event.target.closest('dialog[open]') !== null;
  return (
    !event.defaultPrevented &&
    !inDialog &&
    (event.ctrlKey || event.metaKey) &&
    !event.altKey &&
    event.key.toLowerCase() === 'k'
  );
}

/** Administration's only keyboard shortcut: it has no globe, map or rail single keys. */
export function usePaletteShortcut(): void {
  const openPalette = useShellStore((state) => state.openPalette);
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!isPaletteShortcut(event)) return;
      event.preventDefault();
      openPalette();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [openPalette]);
}
