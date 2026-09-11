import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

import { viewTitle } from './TopBar';
import { isEditableTarget } from './useViewShortcuts';

// Load real route modules before timing keyboard transitions into the map.
beforeAll(async () => {
  await Promise.all([
    import('@/features/globe/GlobePage'),
    import('@/features/research/ResearchPage'),
  ]);
});

describe('AppShell', () => {
  it('lets the keyboard skip repeated navigation and focus the main area', async () => {
    const { user } = renderApp('/', 'user');
    const skip = await screen.findByRole('link', { name: 'Skip to main content' });
    await user.tab();
    expect(skip).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('main')).toHaveFocus();
  });

  it('shows the brand, the rail items and the user', async () => {
    renderApp('/', 'user');
    expect(await screen.findByRole('img', { name: 'The All Seeing Eye' })).toBeInTheDocument();
    expect(screen.getByText('The All Seeing Eye')).toBeInTheDocument();
    expect(screen.getByText('Uma User')).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('link', { name: 'Saved reports' })).toHaveAttribute(
      'href',
      '/reports',
    );
    expect(within(nav).getByRole('link', { name: 'Live monitor' })).toHaveAttribute(
      'href',
      '/trackers',
    );
    expect(within(nav).queryByRole('link', { name: 'Direction' })).not.toBeInTheDocument();
    expect(within(nav).getByRole('link', { name: 'Alerts' })).toHaveAttribute('href', '/warning');
    expect(within(nav).queryByRole('link', { name: 'Users' })).not.toBeInTheDocument();
    expect(screen.getByText('Globe', { selector: 'p' })).toBeInTheDocument();
  });

  it('shows a single administration entry only to admins', async () => {
    renderApp('/', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('link', { name: 'Administration' })).toHaveAttribute(
      'href',
      '/admin',
    );
    expect(within(nav).queryByRole('link', { name: 'Users' })).not.toBeInTheDocument();
  });

  it('uses one Map destination while preserving the projection and keyboard controls', async () => {
    const { user } = renderApp('/', 'user');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    const map = within(nav).getByRole('link', { name: 'Map' });
    expect(map).toHaveAttribute('aria-current', 'page');
    expect(within(nav).queryByText('Globe')).not.toBeInTheDocument();
    await user.click(map);
    expect(useGlobeStore.getState().mode).toBe('globe');
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('map');
    await user.click(map);
    expect(useGlobeStore.getState().mode).toBe('map');
    await user.keyboard('G');
    expect(useGlobeStore.getState().mode).toBe('globe');
  });

  it('ignores shortcuts with modifiers or inside form fields', async () => {
    const { user } = renderApp('/research', 'user');
    // Shortcut behaviour starts after the lazy route module has loaded.
    await act(async () => {
      await vi.dynamicImportSettled();
    });
    const input = await screen.findByRole('textbox', { name: 'Your question' });
    await user.type(input, 'm');
    expect(useGlobeStore.getState().mode).toBe('globe');
    expect(input).toHaveValue('m');
    fireEvent.keyDown(window, { key: 'm', ctrlKey: true });
    expect(useGlobeStore.getState().mode).toBe('globe');
  });

  it('returns to the map workspace without changing the chosen projection', async () => {
    const { user, router } = renderApp('/reports', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    expect(screen.getByText('Saved reports', { selector: 'p' })).toBeInTheDocument();
    await user.click(within(nav).getByRole('link', { name: 'Map' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/');
    });
    expect(useGlobeStore.getState().mode).toBe('globe');
  });

  it('logs out and returns to the login page', async () => {
    const { user, router } = renderApp('/', 'user');
    await user.click(await screen.findByRole('button', { name: 'Logout' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it('derives the top bar title and detects editable targets', () => {
    expect(viewTitle('/', 'globe')).toBe('Globe');
    expect(viewTitle('/', 'map')).toBe('Map');
    expect(viewTitle('/admin/audit', 'globe')).toBe('Admin');
    expect(viewTitle('/warning', 'globe')).toBe('Alerts');
    expect(viewTitle('/elsewhere', 'globe')).toBe('The All Seeing Eye');

    const editable = document.createElement('div');
    editable.contentEditable = 'true';
    expect(isEditableTarget(editable)).toBe(true);
    expect(isEditableTarget(document.createElement('textarea'))).toBe(true);
    expect(isEditableTarget(document.createElement('div'))).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});
