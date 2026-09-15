import { screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { useShellStore } from '@/stores/shell';
import { renderApp } from '@/test/render';

afterEach(() => {
  useShellStore.getState().setRailCollapsed(false);
});

describe('administration shell chrome', () => {
  it('shows a breadcrumb for the current section and page', async () => {
    const { user, router } = renderApp('/admin/users', 'admin');
    await screen.findByRole('heading', { name: 'Users', level: 1 });
    const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' });
    expect(within(crumbs).getByText('Access and teams')).toBeInTheDocument();
    expect(within(crumbs).getByText('Users')).toHaveAttribute('aria-current', 'page');
    await user.click(within(crumbs).getByRole('link', { name: 'Administration' }));
    expect(router.state.location.pathname).toBe('/admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    const overview = screen.getByRole('navigation', { name: 'Breadcrumb' });
    expect(within(overview).queryByRole('link')).not.toBeInTheDocument();
  });

  it('links the verified session indicator to security settings', async () => {
    const { user, router } = renderApp('/admin/audit', 'admin');
    await screen.findByRole('heading', { name: 'Audit log', level: 1 });
    await user.click(
      screen.getByRole('link', { name: 'Verified administrator session: security settings' }),
    );
    expect(router.state.location.pathname).toBe('/admin/security');
  });

  it('collapses the rail to icons while keeping accessible link names', async () => {
    const { user } = renderApp('/admin/sources', 'admin');
    await screen.findByRole('heading', { name: 'Sources', level: 1 });
    const toggle = screen.getByRole('button', { name: 'Collapse navigation' });
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await user.click(toggle);

    const expand = screen.getByRole('button', { name: 'Expand navigation' });
    expect(expand).toHaveAttribute('aria-pressed', 'true');
    const nav = screen.getByRole('navigation', { name: 'Administration' });
    expect(within(nav).getByRole('link', { name: 'Sources' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(nav).getByRole('link', { name: 'Sources' })).toHaveAttribute('title', 'Sources');
    expect(within(nav).queryByText('Research services')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Return to research' })).toHaveAttribute(
      'title',
      'Return to research',
    );

    await user.click(expand);
    expect(within(nav).getByText('Research services')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Collapse navigation' })).toBeInTheDocument();
  });
});
