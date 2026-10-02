import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';

import { useAssistantPosition } from './useAssistantPosition';

const originalSize = { width: window.innerWidth, height: window.innerHeight };
afterEach(() => {
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: originalSize.width },
    innerHeight: { configurable: true, value: originalSize.height },
  });
});

function Launcher() {
  const movement = useAssistantPosition();
  const [opened, setOpened] = useState(0);
  return (
    <>
      <button
        style={{ left: movement.position.x, top: movement.position.y }}
        data-dragging={movement.dragging}
        onPointerDown={movement.onPointerDown}
        onPointerMove={movement.onPointerMove}
        onPointerUp={movement.onPointerUp}
        onPointerCancel={movement.onPointerCancel}
        onKeyDown={movement.onKeyDown}
        onClick={() => {
          if (movement.allowClick()) setOpened((value) => value + 1);
        }}
      >
        Launcher
      </button>
      <output aria-label="Open count">{opened}</output>
      <p role="status" aria-label="Position announcement">
        {movement.announcement}
      </p>
    </>
  );
}

function pointer(element: HTMLElement, kind: string, x: number, y: number, button = 0) {
  const event = new MouseEvent(kind, { bubbles: true, clientX: x, clientY: y, button });
  Object.defineProperty(event, 'pointerId', { value: 7 });
  fireEvent(element, event);
}

it('ignores hover, secondary-button movement and small primary movement without eating a click', () => {
  render(<Launcher />);
  const launcher = screen.getByRole('button', { name: 'Launcher' });
  const start = launcher.style.cssText;
  pointer(launcher, 'pointermove', 30, 30);
  pointer(launcher, 'pointerdown', 10, 10, 2);
  pointer(launcher, 'pointermove', 30, 30, 2);
  pointer(launcher, 'pointerup', 30, 30, 2);
  pointer(launcher, 'pointerdown', 10, 10);
  pointer(launcher, 'pointermove', 13, 13);
  expect(launcher).toHaveAttribute('data-dragging', 'false');
  pointer(launcher, 'pointerup', 13, 13);
  fireEvent.click(launcher);
  expect(launcher.style.cssText).toBe(start);
  expect(screen.getByLabelText('Open count')).toHaveTextContent('1');
});

it('releases capture on cancellation and suppresses only the click following a drag', () => {
  render(<Launcher />);
  const launcher = screen.getByRole('button', { name: 'Launcher' });
  const capture = vi.fn();
  const release = vi.fn();
  const hasCapture = vi.fn(() => true);
  Object.assign(launcher, {
    setPointerCapture: capture,
    releasePointerCapture: release,
    hasPointerCapture: hasCapture,
  });
  pointer(launcher, 'pointerdown', 100, 100);
  expect(capture).toHaveBeenCalledWith(7);
  pointer(launcher, 'pointermove', -2000, -2000);
  pointer(launcher, 'pointermove', -2001, -2001);
  expect(launcher).toHaveStyle({ left: '12px', top: '12px' });
  expect(launcher).toHaveAttribute('data-dragging', 'true');
  pointer(launcher, 'pointercancel', -2001, -2001);
  expect(release).toHaveBeenCalledWith(7);
  expect(launcher).toHaveAttribute('data-dragging', 'false');
  fireEvent.click(launcher);
  expect(screen.getByLabelText('Open count')).toHaveTextContent('0');
  fireEvent.click(launcher);
  expect(screen.getByLabelText('Open count')).toHaveTextContent('1');
  hasCapture.mockReturnValue(false);
  pointer(launcher, 'pointerup', 0, 0);
  expect(release).toHaveBeenCalledTimes(1);
});

it('supports accelerated keyboard movement, clamps after resize and removes its resize listener', () => {
  const add = vi.spyOn(window, 'addEventListener');
  const remove = vi.spyOn(window, 'removeEventListener');
  const { unmount } = render(<Launcher />);
  const launcher = screen.getByRole('button', { name: 'Launcher' });
  const start = { x: parseInt(launcher.style.left), y: parseInt(launcher.style.top) };
  fireEvent.keyDown(launcher, { key: 'ArrowLeft', shiftKey: true });
  fireEvent.keyDown(launcher, { key: 'ArrowUp' });
  expect(launcher).toHaveStyle({ left: `${start.x - 48}px`, top: `${start.y - 16}px` });
  fireEvent.keyDown(launcher, { key: 'ArrowRight' });
  fireEvent.keyDown(launcher, { key: 'ArrowDown' });
  expect(launcher).toHaveStyle({ left: `${start.x - 32}px`, top: `${start.y}px` });
  const unrelated = new KeyboardEvent('keydown', {
    key: 'Escape',
    bubbles: true,
    cancelable: true,
  });
  fireEvent(launcher, unrelated);
  expect(unrelated.defaultPrevented).toBe(false);
  expect(screen.getByRole('status', { name: 'Position announcement' })).toHaveTextContent(
    'Eye assistant moved.',
  );
  Object.defineProperties(window, {
    innerWidth: { configurable: true, value: 320 },
    innerHeight: { configurable: true, value: 260 },
  });
  fireEvent(window, new Event('resize'));
  expect(launcher).toHaveStyle({ left: '172px', top: '166px' });
  fireEvent.keyDown(launcher, { key: 'Home' });
  expect(launcher).toHaveStyle({ left: '164px', top: '150px' });
  expect(screen.getByRole('status', { name: 'Position announcement' })).toHaveTextContent(
    'Eye assistant position reset.',
  );
  const resize = add.mock.calls.find(([name]) => name === 'resize')?.[1];
  unmount();
  expect(resize).toBeTypeOf('function');
  expect(remove).toHaveBeenCalledWith('resize', resize);
});
