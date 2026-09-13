import { act, fireEvent, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { useShellStore } from '@/stores/shell';
import { renderApp } from '@/test/render';

describe('collapsible rail', () => {
  beforeEach(() => {
    useShellStore.setState({ railCollapsed: false });
  });

  it('collapses to icons, keeps every destination reachable and restores on demand', async () => {
    const { user } = renderApp('/research', 'admin');
    const nav = await screen.findByRole('navigation', { name: 'Primary' });
    const rail = nav.closest('aside');
    expect(rail).not.toHaveAttribute('data-collapsed');
    await user.click(screen.getByRole('button', { name: 'Collapse navigation' }));
    expect(rail).toHaveAttribute('data-collapsed', 'true');
    expect(useShellStore.getState().railCollapsed).toBe(true);
    expect(within(nav).getByRole('link', { name: 'Cyber intelligence' })).toHaveAttribute(
      'title',
      'Cyber intelligence',
    );
    expect(within(nav).getByRole('link', { name: 'Administration' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Expand navigation' }));
    expect(rail).not.toHaveAttribute('data-collapsed');
  });

  it('toggles with the [ key outside form fields and shows a UTC clock', async () => {
    renderApp('/research', 'user');
    await screen.findByRole('navigation', { name: 'Primary' });
    act(() => {
      fireEvent.keyDown(window, { key: '[' });
    });
    expect(useShellStore.getState().railCollapsed).toBe(true);
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toBeInTheDocument();
    expect(screen.getByLabelText('Current time, UTC')).toHaveTextContent('UTC');
  });
});
