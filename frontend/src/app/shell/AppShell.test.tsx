import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

import { viewTitle } from './TopBar';
import { isEditableTarget } from './useViewShortcuts';

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
    expect(within(nav).getByRole('link', { name: 'Reports' })).toHaveAttribute('href', '/reports');
    expect(within(nav).getByRole('link', { name: 'Trackers' })).toHaveAttribute(
      'href',
      '/trackers',
    );
    expect(within(nav).getByRole('link', { name: 'Direction' })).toHaveAttribute(
      'href',
      '/direction',
    );
    expect(within(nav).getByRole('link', { name: 'Warning' })).toHaveAttribute('href', '/warning');
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

  it('switches between globe and map with the rail and the G and M keys', async () => {
    const { user } = renderApp('/', 'user');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    const globe = within(nav).getByRole('button', { name: /^Globe/ });
    const map = within(nav).getByRole('button', { name: /^Map/ });
    expect(globe).toHaveAttribute('aria-pressed', 'true');

    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('map');
    expect(map).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Map', { selector: 'p' })).toBeInTheDocument();

    await user.keyboard('G');
    expect(useGlobeStore.getState().mode).toBe('globe');

    await user.click(map);
    expect(useGlobeStore.getState().mode).toBe('map');
    await user.click(globe);
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

  it('navigates home when a rail mode button is used from another page', async () => {
    const { user, router } = renderApp('/reports', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    expect(screen.getByText('Reports', { selector: 'p' })).toBeInTheDocument();
    await user.click(within(nav).getByRole('button', { name: /^Map/ }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/');
    });
    expect(useGlobeStore.getState().mode).toBe('map');
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
    expect(viewTitle('/warning', 'globe')).toBe('Warning');
    expect(viewTitle('/elsewhere', 'globe')).toBe('The All Seeing Eye');

    const editable = document.createElement('div');
    editable.contentEditable = 'true';
    expect(isEditableTarget(editable)).toBe(true);
    expect(isEditableTarget(document.createElement('textarea'))).toBe(true);
    expect(isEditableTarget(document.createElement('div'))).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});
