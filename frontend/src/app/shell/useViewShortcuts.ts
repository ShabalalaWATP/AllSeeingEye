import { useEffect } from 'react';

import { useGlobeStore } from '@/stores/globe';
import { usePreferencesStore } from '@/stores/preferences';
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
 * Keyboard shortcuts: Ctrl or Cmd K search, G globe, M map, O ops room, [ toggles the
 * rail and ? opens the shortcut help. The single-key ones are ignored in form fields and
 * dialogs, and are off entirely when the user turns single-key shortcuts off.
 */
export function useViewShortcuts(): void {
  const { showGlobe, showMap } = useViewNavigation();
  const setOpsRoom = useGlobeStore((state) => state.setOpsRoom);
  const toggleRail = useShellStore((state) => state.toggleRail);
  const openPalette = useShellStore((state) => state.openPalette);
  const singleKey = usePreferencesStore((state) => state.singleKeyShortcuts);
  const openHelp = usePreferencesStore((state) => state.openShortcutHelp);

  useEffect(() => {
    const actions: Record<string, () => void> = {
      g: showGlobe,
      m: showMap,
      o: () => {
        showGlobe();
        setOpsRoom(true);
      },
      '[': toggleRail,
      // The help lives in the top bar, which the ops room hides.
      '?': () => {
        setOpsRoom(false);
        openHelp();
      },
    };
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
      if (key === 'escape') {
        setOpsRoom(false);
        return;
      }
      const action = singleKey ? actions[key] : undefined;
      if (action === undefined) return;
      event.preventDefault();
      action();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [openHelp, openPalette, setOpsRoom, showGlobe, showMap, singleKey, toggleRail]);
}
