import { screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { installDialogStub } from '@/test/dialogStub';
import { renderApp } from '@/test/render';
import { useShellStore } from '@/stores/shell';

// Each administration module records when it is first imported. Module loading is cached,
// so every ordinary-account check in this file runs before the administrator control.
const loaded = vi.hoisted(() => new Set<string>());
vi.mock('@/app/shell/AdminShell', async (original) => {
  loaded.add('AdminShell');
  return original();
});
vi.mock('@/app/shell/AdminPalette', async (original) => {
  loaded.add('AdminPalette');
  return original();
});
vi.mock('@/app/router/AdminSessionGate', async (original) => {
  loaded.add('AdminSessionGate');
  return original();
});
vi.mock('@/features/admin/AdminOverviewPage', async (original) => {
  loaded.add('AdminOverviewPage');
  return original();
});

let narrow = false;

beforeEach(() => {
  const base = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => {
    const media = base(query);
    if (query.includes('max-width')) Object.defineProperty(media, 'matches', { get: () => narrow });
    return media;
  });
});

afterEach(() => {
  narrow = false;
  useShellStore.setState({ paletteOpen: false });
  vi.restoreAllMocks();
});

installDialogStub();

describe('administration stays out of ordinary accounts', () => {
  it.each([
    ['narrow', true],
    ['wide', false],
  ])(
    'renders no admin control and loads no admin module on a %s screen',
    async (_width, isNarrow) => {
      narrow = isNarrow;
      const { user } = renderApp('/research/saved', 'user');
      await screen.findByRole('heading', { name: 'Saved research', level: 1 });
      expect(screen.queryByRole('link', { name: 'Go to Administration' })).not.toBeInTheDocument();
      if (isNarrow) {
        await user.click(screen.getByRole('button', { name: 'Open navigation' }));
        const dialog = screen.getByRole('dialog', { name: 'Navigation' });
        expect(
          within(dialog).queryByRole('list', { name: 'Switch workspace' }),
        ).not.toBeInTheDocument();
        await user.click(within(dialog).getByRole('button', { name: 'Close navigation' }));
      } else {
        const rail = screen.getByRole('navigation', { name: 'Primary' });
        expect(
          within(rail).queryByRole('link', { name: 'Administration' }),
        ).not.toBeInTheDocument();
      }
      await user.keyboard('{Control>}k{/Control}');
      const palette = await screen.findByRole('dialog', { name: 'Find anything' });
      await user.type(within(palette).getByRole('combobox'), 'administration');
      expect(
        within(palette).queryByRole('option', { name: /^Administration/ }),
      ).not.toBeInTheDocument();
      expect([...loaded]).toEqual([]);
    },
  );

  it('loads no admin module when an ordinary account requests an admin page', async () => {
    renderApp('/admin/users', 'user');
    expect(await screen.findByText('Admin access required')).toBeInTheDocument();
    expect([...loaded]).toEqual([]);
  });

  // Proves the module checks above would notice a load.
  it('loads the administration shell only once an administrator switches', async () => {
    const { user } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    expect([...loaded]).toEqual([]);
    await user.click(screen.getByRole('link', { name: 'Go to Administration' }));
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    expect(loaded).toEqual(new Set(['AdminSessionGate', 'AdminShell', 'AdminOverviewPage']));
  });
});
