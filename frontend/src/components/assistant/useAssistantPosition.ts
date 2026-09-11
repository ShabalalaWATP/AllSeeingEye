import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, PointerEvent } from 'react';

const WIDTH = 76,
  HEIGHT = 56,
  MARGIN = 12;
interface Position {
  x: number;
  y: number;
}
const viewport = () => ({ width: window.innerWidth, height: window.innerHeight });
export function clampAssistantPosition(position: Position, size = viewport()): Position {
  return {
    x: Math.max(MARGIN, Math.min(size.width - WIDTH - MARGIN, position.x)),
    y: Math.max(MARGIN, Math.min(size.height - HEIGHT - MARGIN, position.y)),
  };
}
const home = () =>
  clampAssistantPosition({
    x: window.innerWidth - WIDTH - 20,
    y: window.innerHeight - HEIGHT - 28,
  });

/** Pointer movement stays local; nothing subscribes map rendering to this position. */
export function useAssistantPosition() {
  const [position, setPosition] = useState(home);
  const [dragging, setDragging] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const drag = useRef<{ x: number; y: number; origin: Position; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  useEffect(() => {
    const resize = () => setPosition((previous) => clampAssistantPosition(previous));
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);
  const onPointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) return;
    drag.current = { x: event.clientX, y: event.clientY, origin: position, moved: false };
    suppressClick.current = false;
    if (typeof event.currentTarget.setPointerCapture === 'function')
      event.currentTarget.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    const active = drag.current;
    if (!active) return;
    const dx = event.clientX - active.x,
      dy = event.clientY - active.y;
    if (!active.moved && Math.hypot(dx, dy) < 6) return;
    active.moved = true;
    setDragging(true);
    setPosition(clampAssistantPosition({ x: active.origin.x + dx, y: active.origin.y + dy }));
  };
  const finish = (event: PointerEvent<HTMLButtonElement>) => {
    suppressClick.current = drag.current?.moved ?? false;
    drag.current = null;
    setDragging(false);
    if (
      typeof event.currentTarget.hasPointerCapture === 'function' &&
      event.currentTarget.hasPointerCapture(event.pointerId)
    )
      event.currentTarget.releasePointerCapture(event.pointerId);
  };
  const reset = () => {
    setPosition(home());
    setAnnouncement('Eye assistant position reset.');
  };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const vectors: Record<string, Position> = {
      ArrowLeft: { x: -1, y: 0 },
      ArrowRight: { x: 1, y: 0 },
      ArrowUp: { x: 0, y: -1 },
      ArrowDown: { x: 0, y: 1 },
    };
    if (event.key === 'Home') {
      event.preventDefault();
      reset();
      return;
    }
    const direction = vectors[event.key];
    if (!direction) return;
    event.preventDefault();
    const step = event.shiftKey ? 48 : 16;
    setPosition((old) =>
      clampAssistantPosition({ x: old.x + direction.x * step, y: old.y + direction.y * step }),
    );
    setAnnouncement('Eye assistant moved. Press Home to reset its position.');
  };
  return {
    position,
    dragging,
    announcement,
    reset,
    onPointerDown,
    onPointerMove,
    onPointerUp: finish,
    onPointerCancel: finish,
    onKeyDown,
    allowClick: () => {
      const allowed = !suppressClick.current;
      suppressClick.current = false;
      return allowed;
    },
  };
}
