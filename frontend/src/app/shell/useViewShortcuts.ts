import { useEffect } from 'react';

import { useGlobeStore } from '@/stores/globe';
import { useShellStore } from '@/stores/shell';

import { useViewNavigation } from './useViewNavigation';

/** True when the key press happened inside a form control or editable region. */
export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  // isContentEditable is not implemented everywhere (jsdom), so check the attribute too.
  const editable = target.getAttribute('contenteditable');
  if (target.isContentEditable || target.contentEditable === 'true' || editable === '') {
    return true;
  }
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
}

/**
 * Keyboard shortcuts: Ctrl or Cmd K search, G globe, M map, O ops room, [ toggles
 * the rail. The single-letter ones are ignored in form fields.
 */
export function useViewShortcuts(): void {
  const { showGlobe, showMap } = useViewNavigation();
  const setOpsRoom = useGlobeStore((state) => state.setOpsRoom);
  const toggleRail = useShellStore((state) => state.toggleRail);
  const openPalette = useShellStore((state) => state.openPalette);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const inDialog =
        event.target instanceof Element && event.target.closest('dialog[open]') !== null;
      if (
        !event.defaultPrevented &&
        !inDialog &&
        (event.ctrlKey || event.metaKey) &&
        !event.altKey &&
        event.key.toLowerCase() === 'k'
      ) {
        event.preventDefault();
        openPalette();
        return;
      }
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      if (isEditableTarget(event.target)) return;
      if (inDialog) return;
      const key = event.key.toLowerCase();
      if (key === 'g') {
        event.preventDefault();
        showGlobe();
      } else if (key === 'm') {
        event.preventDefault();
        showMap();
      } else if (key === 'o') {
        event.preventDefault();
        showGlobe();
        setOpsRoom(true);
      } else if (key === '[') {
        event.preventDefault();
        toggleRail();
      } else if (key === 'escape') {
        setOpsRoom(false);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [openPalette, setOpsRoom, showGlobe, showMap, toggleRail]);
}
