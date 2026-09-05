import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { renderApp } from '@/test/render';

import { viewTitle } from './TopBar';
import { isEditableTarget } from './useViewShortcuts';

describe('AppShell', () => {
  it('shows the brand, the rail items with phase labels, and the user', async () => {
    renderApp('/', 'user');
    expect(await screen.findByRole('img', { name: 'The All Seeing Eye' })).toBeInTheDocument();
    expect(screen.getByText('The All Seeing Eye')).toBeInTheDocument();
    expect(screen.getByText('Uma User')).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('link', { name: 'Reports' })).toHaveAttribute('href', '/reports');
    for (const [label, phase] of [
      ['Trackers', 'Phase 3'],
      ['Direction', 'Phase 4'],
    ]) {
      const button = within(nav).getByRole('button', { name: new RegExp(`^${label!}`) });
      expect(button).toBeDisabled();
      expect(button).toHaveTextContent(phase!);
    }
    expect(within(nav).queryByRole('link', { name: 'Users' })).not.toBeInTheDocument();
    expect(screen.getByText('Globe', { selector: 'p' })).toBeInTheDocument();
  });

  it('shows the admin links only to admins', async () => {
    renderApp('/', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    expect(within(nav).getByRole('link', { name: 'Account requests' })).toHaveAttribute(
      'href',
      '/admin/requests',
    );
    expect(within(nav).getByRole('link', { name: 'Users' })).toHaveAttribute(
      'href',
      '/admin/users',
    );
    expect(within(nav).getByRole('link', { name: 'Audit log' })).toHaveAttribute(
      'href',
      '/admin/audit',
    );
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
    const { user } = renderApp('/admin/requests', 'admin');
    await screen.findByRole('heading', { name: 'Account requests' });
    const row = (await screen.findByText('Nia Newcomer')).closest('tr')!;
    await user.click(within(row).getByRole('button', { name: 'Reject' }));
    const input = within(row).getByLabelText('Reason (optional)');
    await user.type(input, 'm');
    expect(useGlobeStore.getState().mode).toBe('globe');
    expect(input).toHaveValue('m');

    fireEvent.keyDown(window, { key: 'm', ctrlKey: true });
    expect(useGlobeStore.getState().mode).toBe('globe');
    fireEvent.keyDown(within(row).getByLabelText('Role'), { key: 'm' });
    expect(useGlobeStore.getState().mode).toBe('globe');
  });

  it('navigates home when a rail mode button is used from another page', async () => {
    const { user, router } = renderApp('/admin/users', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    expect(screen.getByText('Admin', { selector: 'p' })).toBeInTheDocument();
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
    expect(viewTitle('/elsewhere', 'globe')).toBe('The All Seeing Eye');

    const editable = document.createElement('div');
    editable.contentEditable = 'true';
    expect(isEditableTarget(editable)).toBe(true);
    expect(isEditableTarget(document.createElement('textarea'))).toBe(true);
    expect(isEditableTarget(document.createElement('div'))).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});
