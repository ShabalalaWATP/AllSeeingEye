import { screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { useGlobeStore } from '@/stores/globe';
import { expectLabelInName } from '@/test/labelInName';
import { renderApp } from '@/test/render';

function control(text: string): HTMLElement {
  const element = screen.getByText(text).closest<HTMLElement>('a, button');
  if (element === null) throw new Error(`No control shows "${text}".`);
  return element;
}

afterEach(() => {
  useGlobeStore.setState({ opsRoom: false });
});

describe('shell controls name themselves by their visible labels (WCAG 2.5.3)', () => {
  it('starts the ops room exit name with its visible text', async () => {
    const { user } = renderApp('/', 'user');
    await screen.findByRole('navigation', { name: 'Primary' });
    await user.keyboard('o');
    const exit = await screen.findByRole('button', { name: /^Ops room · Esc to exit/ });
    expect(exit).toBe(control('Ops room · Esc to exit'));
    expectLabelInName(exit);
  });

  it('names the verified session link with its visible label', async () => {
    renderApp('/admin/audit', 'admin');
    await screen.findByRole('heading', { name: 'Audit log', level: 1 });
    const session = control('Verified session');
    expect(session).toHaveAttribute('href', '/admin/security');
    expectLabelInName(session);
  });

  it('includes the visible display name in the profile link name', async () => {
    renderApp('/research', 'user');
    await screen.findByRole('navigation', { name: 'Primary' });
    const profile = control('Uma User');
    expect(profile).toHaveAttribute('href', '/account');
    expectLabelInName(profile);
  });

  it('announces the home link once, with the brand mark decorative', async () => {
    renderApp('/research', 'user');
    const rail = (await screen.findByRole('navigation', { name: 'Primary' })).closest('aside');
    if (rail === null) throw new Error('The rail is missing.');
    const home = within(rail).getByRole('link', { name: 'The All Seeing Eye' });
    expect(home).toHaveAttribute('href', '/');
    expect(within(home).queryByRole('img')).not.toBeInTheDocument();
    expectLabelInName(home);
  });

  it('announces the administration home link without repeating the brand', async () => {
    renderApp('/admin/audit', 'admin');
    await screen.findByRole('heading', { name: 'Audit log', level: 1 });
    // jsdom applies no layout, so the stacked lines join without spaces here.
    const home = screen.getByRole('link', {
      name: /^The All Seeing Eye\s*Administration\s*Ops$/,
    });
    expect(home).toHaveAttribute('href', '/admin');
    expectLabelInName(home);
  });
});
