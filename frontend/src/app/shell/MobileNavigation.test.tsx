import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

let change: (() => void) | undefined;
let narrow = true;

beforeEach(() => {
  const base = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = base(query);
    if (query.includes('max-width')) {
      Object.defineProperty(media, 'matches', { get: () => narrow });
      media.addEventListener = (
        _type: string,
        listener: EventListenerOrEventListenerObject | null,
      ) => {
        change = listener as () => void;
      };
      media.removeEventListener = () => {
        change = undefined;
      };
    }
    return media;
  });
  // jsdom has no native dialog top layer. Real browser checks cover its focus trap.
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
  narrow = true;
  change = undefined;
  vi.restoreAllMocks();
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
});

describe('mobile navigation', () => {
  it('opens one navigation dialog, closes on cancel, and returns focus to its trigger', async () => {
    const { user } = renderApp('/', 'user');
    const trigger = await screen.findByRole('button', { name: 'Open navigation' });
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Navigation' });
    expect(within(dialog).getByRole('button', { name: 'Close navigation' })).toHaveFocus();
    fireEvent(dialog, new Event('cancel', { cancelable: true }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
  });

  it('closes on a destination and on a same-page view change', async () => {
    const { user, router } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Open navigation' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('link', { name: 'Research' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/research');
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open navigation' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('link', { name: 'Map' }));
    expect(useGlobeStore.getState().mode).toBe('globe');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('ignores global view shortcuts in the dialog and preserves ordinary shortcuts outside it', async () => {
    const { user } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Open navigation' }));
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('globe');
    await user.click(screen.getByRole('button', { name: 'Close navigation' }));
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('map');
  });

  it('provides a separate admin menu and returns focus before returning to research', async () => {
    const { user, router } = renderApp('/admin', 'admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    const trigger = screen.getByRole('button', { name: 'Open administration navigation' });
    await user.click(trigger);
    const dialog = screen.getByRole('dialog', { name: 'Administration navigation' });
    expect(within(dialog).getByRole('navigation', { name: 'Administration' })).toBeInTheDocument();
    expect(within(dialog).queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole('button', { name: 'Close navigation' }));
    await waitFor(() => {
      expect(trigger).toHaveFocus();
    });
    await user.click(trigger);
    await user.click(within(screen.getByRole('dialog')).getByRole('link', { name: 'Users' }));
    expect(router.state.location.pathname).toBe('/admin/users');
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    await screen.findByText('Uma User');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open administration navigation' }));
    act(() => {
      narrow = false;
      change?.();
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    act(() => {
      narrow = true;
      change?.();
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open administration navigation' }));
    await user.click(
      within(screen.getByRole('dialog')).getByRole('link', { name: 'Return to research' }),
    );
    expect(router.state.location.pathname).toBe('/');
    expect(screen.getByRole('button', { name: 'Open navigation' })).toBeInTheDocument();
  });

  it('switches to a single desktop rail on resize', async () => {
    const { user } = renderApp('/', 'admin');
    await user.click(await screen.findByRole('button', { name: 'Open navigation' }));
    act(() => {
      narrow = false;
      change?.();
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Open navigation' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('navigation', { name: 'Primary' })).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Administration' })).toBeInTheDocument();
    act(() => {
      narrow = true;
      change?.();
    });
    expect(screen.getByRole('button', { name: 'Open navigation' })).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
