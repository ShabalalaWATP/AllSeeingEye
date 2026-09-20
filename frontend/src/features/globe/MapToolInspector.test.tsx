import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { MapToolInspector } from './MapToolInspector';

function pointer(target: HTMLElement, type: string, clientX: number, button = 0) {
  const event = new MouseEvent(type, { bubbles: true, clientX, button });
  Object.defineProperty(event, 'pointerId', { value: 7 });
  fireEvent(target, event);
}

it.each(['left', 'right'] as const)(
  'drags the %s inspector edge, clamps its width and ignores movements after release',
  (side) => {
    render(
      <MapToolInspector id="study" label="Study" icon="rf" side={side} onClose={vi.fn()}>
        <p>Study inputs</p>
      </MapToolInspector>,
    );
    const slider = screen.getByRole('slider', { name: 'Resize tool panel' });
    const capture = vi.fn();
    Object.defineProperty(slider, 'setPointerCapture', { value: capture });
    const direction = side === 'left' ? 1 : -1;
    pointer(slider, 'pointermove', 300);
    expect(slider).toHaveAttribute('aria-valuenow', '360');
    pointer(slider, 'pointerdown', 400, 2);
    pointer(slider, 'pointermove', 400 + direction * 80);
    expect(capture).not.toHaveBeenCalled();
    expect(slider).toHaveAttribute('aria-valuenow', '360');
    pointer(slider, 'pointerdown', 400);
    expect(capture).toHaveBeenCalledWith(7);
    pointer(slider, 'pointermove', 400 + direction * 80);
    expect(slider).toHaveAttribute('aria-valuenow', '440');
    expect(screen.getByRole('region', { name: 'Study' })).toHaveStyle({
      '--map-inspector-width': '440px',
    });
    pointer(slider, 'pointermove', 400 + direction * 1000);
    expect(slider).toHaveAttribute('aria-valuenow', '600');
    pointer(slider, 'pointermove', 400 - direction * 1000);
    expect(slider).toHaveAttribute('aria-valuenow', '320');
    pointer(slider, 'pointerup', 400);
    pointer(slider, 'pointermove', 400 + direction * 80);
    expect(slider).toHaveAttribute('aria-valuenow', '320');
  },
);

it.each(['pointercancel', 'lostpointercapture'])(
  'stops resizing after %s and does not consume unrelated keyboard input',
  (eventType) => {
    render(
      <MapToolInspector id="study" label="Study" icon="rf" onClose={vi.fn()}>
        <p>Study inputs</p>
      </MapToolInspector>,
    );
    const slider = screen.getByRole('slider', { name: 'Resize tool panel' });
    Object.defineProperty(slider, 'setPointerCapture', { value: vi.fn() });
    pointer(slider, 'pointerdown', 400);
    pointer(slider, 'pointermove', 380);
    expect(slider).toHaveAttribute('aria-valuenow', '380');
    pointer(slider, eventType, 380);
    pointer(slider, 'pointermove', 200);
    expect(slider).toHaveAttribute('aria-valuenow', '380');
    expect(fireEvent.keyDown(slider, { key: 'Tab' })).toBe(true);
    expect(slider).toHaveAttribute('aria-valuenow', '380');
  },
);
