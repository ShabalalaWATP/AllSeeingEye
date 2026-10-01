import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { useLocation } from 'react-router';

const ITEMS = 'a[href], button:not([disabled])';
/** Targets that take focus on a click, so a click there keeps focus where it lands. */
const CONTROLS =
  'a[href], button, input, select, textarea, summary, [contenteditable="true"], [tabindex]:not([tabindex="-1"])';

function itemsIn(menu: HTMLElement | null): HTMLElement[] {
  return Array.from(menu?.querySelectorAll<HTMLElement>(ITEMS) ?? []);
}

/** Arrow keys wrap around the items; Home and End jump to either end. */
function targetIndex(key: string, current: number, count: number): number | null {
  if (key === 'Home') return 0;
  if (key === 'End') return count - 1;
  if (key === 'ArrowDown') return (current + 1) % count;
  if (key === 'ArrowUp') return current <= 0 ? count - 1 : current - 1;
  return null;
}

/**
 * A disclosure-style menu button: a trigger that shows a short list of links and buttons.
 * Opening moves focus to the first item. Escape, or a click anywhere that is not another
 * control, closes it and returns focus to the trigger. Tabbing away or following a link
 * closes it quietly, and a route change always closes it.
 */
export function useMenuButton() {
  const { key } = useLocation();
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const open = openedAt === key;
  const menuId = useId();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    setOpenedAt(null);
  }, []);
  const toggle = () => {
    setOpenedAt(open ? null : key);
  };

  useEffect(() => {
    if (open) itemsIn(menuRef.current)[0]?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const outside = (target: EventTarget | null) =>
      !(target instanceof Node) || !wrapperRef.current?.contains(target);
    const onPointerDown = (event: PointerEvent) => {
      if (!outside(event.target)) return;
      close();
      const control = event.target instanceof Element && event.target.closest(CONTROLS) !== null;
      // Let the pointer settle focus first, then bring it back from a non-control target.
      // Closing ends this effect, so the timer is not cleared with it; an unmounted
      // trigger leaves the ref empty and nothing moves.
      if (!control) window.setTimeout(() => triggerRef.current?.focus(), 0);
    };
    const onFocusOut = (event: FocusEvent) => {
      if (event.relatedTarget !== null && outside(event.relatedTarget)) close();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        // Stopped here, so window shortcuts such as leaving the ops room do not also fire.
        event.preventDefault();
        event.stopPropagation();
        close();
        triggerRef.current?.focus();
        return;
      }
      const items = itemsIn(menuRef.current);
      const active = document.activeElement;
      const current = active instanceof HTMLElement ? items.indexOf(active) : -1;
      const next = items.length === 0 ? null : targetIndex(event.key, current, items.length);
      if (next === null) return;
      event.preventDefault();
      items[next]?.focus();
    };
    const wrapper = wrapperRef.current;
    document.addEventListener('pointerdown', onPointerDown);
    wrapper?.addEventListener('focusout', onFocusOut);
    wrapper?.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      wrapper?.removeEventListener('focusout', onFocusOut);
      wrapper?.removeEventListener('keydown', onKeyDown);
    };
  }, [open, close]);

  return { open, toggle, close, menuId, wrapperRef, triggerRef, menuRef };
}
