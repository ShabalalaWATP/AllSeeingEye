import { act, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { installDialogStub } from '@/test/dialogStub';
import { renderApp } from '@/test/render';
import { useShellStore } from '@/stores/shell';
import { useWorkspaceReturnStore } from '@/stores/workspaceReturn';

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

function shellHeader(workspace: 'research' | 'admin'): HTMLElement {
  const header = document.querySelector<HTMLElement>(`header[data-workspace="${workspace}"]`);
  if (header === null) throw new Error(`The ${workspace} header is missing.`);
  return header;
}

/** The control sits in the shell header, never inside a menu or dialog. */
function headerSwitch(workspace: 'research' | 'admin', name: string): HTMLElement {
  const control = within(shellHeader(workspace)).getByRole('link', { name });
  expect(control.closest('dialog')).toBeNull();
  // 44 by 44 CSS pixels at least (WCAG 2.5.8); jsdom has no layout, so check the tokens.
  expect(control).toHaveClass('min-h-11', 'min-w-11');
  return control;
}

describe.each([
  ['narrow', true],
  ['wide', false],
])('workspace switch on a %s screen', (_width, isNarrow) => {
  beforeEach(() => {
    narrow = isNarrow;
  });

  it('offers Administration in the research top bar and Research in the admin header', async () => {
    const { user, router } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    const toAdmin = headerSwitch('research', 'Go to Administration');
    expect(toAdmin).toHaveAttribute('href', '/admin');
    expect(toAdmin).toHaveTextContent('Administration');
    await user.click(toAdmin);
    expect(router.state.location.pathname).toBe('/admin');
    const heading = await screen.findByRole('heading', { name: 'Administration', level: 1 });
    // Switching is a navigation, so focus moves to the new page's heading.
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    const toResearch = headerSwitch('admin', 'Go to research workspace');
    expect(toResearch).toHaveTextContent('Research');
    expect(toResearch).toHaveAttribute('href', '/research/saved');
    await user.click(toResearch);
    expect(router.state.location.pathname).toBe('/research/saved');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
  });

  it('marks the administration header with its badge and keeps the session context', async () => {
    renderApp('/admin/users', 'admin');
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    const header = shellHeader('admin');
    const crumbs = within(header).getByRole('navigation', { name: 'Breadcrumb' });
    expect(within(crumbs).getByRole('link', { name: 'Administration' })).toHaveAttribute(
      'href',
      '/admin',
    );
    expect(
      within(header).getByRole('link', { name: /^Verified session Administrator/ }),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(document.title).toBe('Users · Administration · The All Seeing Eye');
    });
  });

  it('shows no workspace switch to an ordinary account', async () => {
    renderApp('/research/saved', 'user');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    expect(screen.queryByRole('link', { name: 'Go to Administration' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Administration/ })).not.toBeInTheDocument();
    expect(document.querySelector('[data-workspace-switch]')).toBeNull();
  });
});

describe('returning to the last route', () => {
  it('returns each way to the page visited last, while explicit routes still win', async () => {
    const { user, router } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    await user.click(screen.getByRole('link', { name: 'Go to Administration' }));
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    const nav = screen.getByRole('navigation', { name: 'Administration' });
    await user.click(within(nav).getByRole('link', { name: 'Users' }));
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    expect(screen.getByRole('link', { name: 'Return to research' })).toHaveAttribute(
      'href',
      '/research/saved',
    );
    await user.click(screen.getByRole('link', { name: 'Return to research' }));
    expect(router.state.location.pathname).toBe('/research/saved');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    // The rail entry and the header switch both reopen the administration page last seen.
    const rail = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(rail).getByRole('list', { name: 'Switch workspace' })).toBeInTheDocument();
    expect(within(rail).getByRole('link', { name: 'Administration' })).toHaveAttribute(
      'href',
      '/admin/users',
    );
    await user.click(screen.getByRole('link', { name: 'Go to Administration' }));
    expect(router.state.location.pathname).toBe('/admin/users');
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    // An explicitly requested route is never redirected to the remembered one.
    await act(() => router.navigate('/admin'));
    expect(router.state.location.pathname).toBe('/admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    await act(() => router.navigate('/'));
    expect(router.state.location.pathname).toBe('/');
    expect(useWorkspaceReturnStore.getState()).toMatchObject({ research: '/', admin: '/admin' });
  });

  it('leads the mobile administration dialog with Return to research', async () => {
    narrow = true;
    const { user } = renderApp('/admin/users', 'admin');
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    await user.click(screen.getByRole('button', { name: 'Open administration navigation' }));
    const dialog = screen.getByRole('dialog', { name: 'Administration navigation' });
    const links = within(dialog).getAllByRole('link');
    // The dialog's home link comes first, then the way back, before any administration page.
    expect(links[1]).toHaveAccessibleName('Return to research');
    expect(links[2]).toHaveAccessibleName('Overview');
  });

  it('leads the mobile research dialog with a headed Administration group', async () => {
    narrow = true;
    const { user } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    await user.click(screen.getByRole('button', { name: 'Open navigation' }));
    const dialog = screen.getByRole('dialog', { name: 'Navigation' });
    const nav = within(dialog).getByRole('navigation', { name: 'Primary' });
    const group = within(nav).getByRole('list', { name: 'Switch workspace' });
    expect(within(group).getByRole('link', { name: 'Administration' })).toBeInTheDocument();
    expect(within(nav).getAllByRole('link')[0]).toHaveAccessibleName('Administration');
  });
});

describe('command palette in both workspaces', () => {
  it('offers Administration from research and the research workspace from administration', async () => {
    const { user, router } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    await user.keyboard('{Control>}k{/Control}');
    let palette = await screen.findByRole('dialog', { name: 'Find anything' });
    await user.type(within(palette).getByRole('combobox'), 'administration');
    await user.click(within(palette).getAllByRole('option', { name: /^Administration/ })[0]!);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/admin');
    });
    await screen.findByRole('heading', { name: 'Administration', level: 1 });

    await user.keyboard('{Control>}k{/Control}');
    palette = await screen.findByRole('dialog', { name: 'Find anything' });
    const search = within(palette).getByRole('combobox');
    expect(search).toHaveAccessibleName('Search administration pages');
    const options = within(palette).getAllByRole('option');
    expect(options[0]).toHaveTextContent(/^Research workspace/);
    // Administration's palette lists administration pages, not the research catalogue.
    expect(within(palette).queryByRole('option', { name: /^Maritime/ })).not.toBeInTheDocument();
    await user.type(search, 'users');
    await user.keyboard('{Enter}');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/admin/users');
    });
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    await user.keyboard('{Control>}k{/Control}');
    palette = await screen.findByRole('dialog', { name: 'Find anything' });
    await user.click(within(palette).getByRole('option', { name: /^Research workspace/ }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/research/saved');
    });
  });
});
