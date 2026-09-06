import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { GlobeControls } from './GlobeControls';

let compact = false;
let media: EventTarget;

beforeEach(() => {
  media = new EventTarget();
  Object.defineProperty(media, 'matches', { get: () => compact });
  vi.spyOn(window, 'matchMedia').mockReturnValue(media as MediaQueryList);
  // jsdom has no top layer. Browser checks verify native focus trapping and inertness.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
      this.querySelector<HTMLElement>('button')?.focus();
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = false;
    },
  });
});

afterEach(() => {
  compact = false;
  vi.restoreAllMocks();
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
});

describe('responsive globe controls', () => {
  it('keeps one persistent control panel on desktop', () => {
    render(
      <GlobeControls>
        <button>Choose layer</button>
      </GlobeControls>,
    );
    expect(screen.getAllByRole('button', { name: 'Choose layer' })).toHaveLength(1);
    expect(screen.queryByRole('button', { name: 'Map controls' })).not.toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('starts closed on mobile and returns focus after native Escape cancellation', async () => {
    compact = true;
    const user = userEvent.setup();
    render(
      <GlobeControls>
        <button>Choose layer</button>
      </GlobeControls>,
    );
    const trigger = screen.getByRole('button', { name: 'Map controls' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('button', { name: 'Choose layer' })).not.toBeInTheDocument();
    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Map controls' });
    expect(within(dialog).getByRole('button', { name: 'Close controls' })).toHaveFocus();
    expect(within(dialog).getByRole('button', { name: 'Choose layer' })).toBeInTheDocument();
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    fireEvent(dialog, new Event('cancel', { cancelable: true }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('allows control interaction and an explicit touch-friendly close action', async () => {
    compact = true;
    const selectLayer = vi.fn();
    const user = userEvent.setup();
    render(
      <GlobeControls>
        <button onClick={selectLayer}>Choose layer</button>
      </GlobeControls>,
    );
    await user.click(screen.getByRole('button', { name: 'Map controls' }));
    await user.click(screen.getByRole('button', { name: 'Choose layer' }));
    expect(selectLayer).toHaveBeenCalledOnce();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close controls' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('dismisses the sheet when resized to desktop and returns to a closed mobile state', async () => {
    compact = true;
    const user = userEvent.setup();
    render(
      <GlobeControls>
        <button>Choose layer</button>
      </GlobeControls>,
    );
    await user.click(screen.getByRole('button', { name: 'Map controls' }));
    act(() => {
      compact = false;
      media.dispatchEvent(new Event('change'));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Choose layer' })).toHaveLength(1);
    act(() => {
      compact = true;
      media.dispatchEvent(new Event('change'));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Choose layer' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Map controls' })).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });

  it('falls back to desktop controls if media queries are unavailable', () => {
    Reflect.deleteProperty(window, 'matchMedia');
    render(
      <GlobeControls>
        <button>Choose layer</button>
      </GlobeControls>,
    );
    expect(screen.getByRole('button', { name: 'Choose layer' })).toBeInTheDocument();
  });
});
