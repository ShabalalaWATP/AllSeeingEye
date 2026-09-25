import { screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { PREFERENCES_KEY, usePreferencesStore } from '@/stores/preferences';
import { renderApp } from '@/test/render';

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
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
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
  usePreferencesStore.setState({ singleKeyShortcuts: true, shortcutHelpOpen: false });
});

describe('keyboard settings', () => {
  it('turns single-key shortcuts off at once and remembers the choice in this browser', async () => {
    const { user } = renderApp('/settings?section=keyboard', 'user');
    const nav = await screen.findByRole('navigation', { name: 'Personal settings' });
    expect(within(nav).getByRole('link', { name: 'Keyboard' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    const toggle = screen.getByRole('checkbox', { name: 'Single-key shortcuts' });
    expect(toggle).toBeChecked();
    expect(toggle).toHaveAccessibleDescription(/Ctrl K search and Esc always work/);
    await user.click(toggle);
    expect(toggle).not.toBeChecked();
    expect(usePreferencesStore.getState().singleKeyShortcuts).toBe(false);
    expect(localStorage.getItem(PREFERENCES_KEY)).toContain('"singleKeyShortcuts":false');
    await user.keyboard('m');
    expect(screen.getByRole('heading', { name: 'Keyboard' })).toBeVisible();
  });

  it('opens the shortcut list from the settings page', async () => {
    const { user } = renderApp('/settings?section=keyboard', 'user');
    await user.click(await screen.findByRole('button', { name: 'Show keyboard shortcuts' }));
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    expect(within(dialog).getByText('Find anything')).toBeInTheDocument();
  });
});
