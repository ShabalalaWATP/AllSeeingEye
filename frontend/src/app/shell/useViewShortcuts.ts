import { useEffect } from 'react';

import { useGlobeStore } from '@/stores/globe';

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

/** Keyboard shortcuts: G shows the globe, M shows the map. Ignored inside form fields. */
export function useViewShortcuts(): void {
  const { showGlobe, showMap } = useViewNavigation();
  const setOpsRoom = useGlobeStore((state) => state.setOpsRoom);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      if (isEditableTarget(event.target)) return;
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
      } else if (key === 'escape') {
        setOpsRoom(false);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [setOpsRoom, showGlobe, showMap]);
}
