import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { SHORTCUT_GROUPS } from '@/lib/keyboardShortcuts';
import { useGlobeStore } from '@/stores/globe';
import { usePreferencesStore } from '@/stores/preferences';
import { useShellStore } from '@/stores/shell';
import { renderApp } from '@/test/render';

beforeEach(() => {
  // jsdom has no native dialog top layer. Real browser checks cover its focus trap.
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
      this.querySelector<HTMLElement>('button, a')?.focus();
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
  useShellStore.setState({ railCollapsed: false, paletteOpen: false });
  useGlobeStore.setState({ opsRoom: false });
});

async function shell() {
  const view = renderApp('/', 'user');
  await screen.findByRole('navigation', { name: 'Primary' });
  return view;
}

describe('keyboard shortcuts', () => {
  it('opens a help dialog listing every shortcut with ?, and closes it with Escape', async () => {
    const { user } = await shell();
    const trigger = screen.getByRole('link', { name: 'Your settings' });
    trigger.focus();
    await user.keyboard('?');
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    for (const group of SHORTCUT_GROUPS) {
      const section = within(dialog).getByRole('region', { name: group.title });
      for (const entry of group.entries) {
        expect(within(section).getByText(entry.action)).toBeInTheDocument();
      }
    }
    expect(within(dialog).getByText('Ctrl K')).toBeInTheDocument();
    expect(within(dialog).queryByText('Off')).not.toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: 'Close' })).toHaveFocus();
    // Keys pressed inside the dialog never reach the global shortcuts.
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('globe');
    fireEvent(dialog, new Event('cancel', { cancelable: true }));
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('closes the help from its button and leaves the ops room to show it', async () => {
    const { user } = await shell();
    await user.keyboard('o');
    expect(useGlobeStore.getState().opsRoom).toBe(true);
    await user.keyboard('?');
    expect(useGlobeStore.getState().opsRoom).toBe(false);
    const dialog = await screen.findByRole('dialog', { name: 'Keyboard shortcuts' });
    await user.click(within(dialog).getByRole('button', { name: 'Close' }));
    expect(usePreferencesStore.getState().shortcutHelpOpen).toBe(false);
  });

  it('turns every single-key shortcut off while Ctrl K and Escape keep working', async () => {
    usePreferencesStore.setState({ singleKeyShortcuts: false });
    const { user } = await shell();
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('globe');
    await user.keyboard('[[');
    expect(useShellStore.getState().railCollapsed).toBe(false);
    await user.keyboard('o');
    expect(useGlobeStore.getState().opsRoom).toBe(false);
    await user.keyboard('?');
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeInTheDocument();
    act(() => {
      useGlobeStore.setState({ opsRoom: true });
    });
    await user.keyboard('{Escape}');
    expect(useGlobeStore.getState().opsRoom).toBe(false);
    await user.keyboard('{Control>}k{/Control}');
    expect(useShellStore.getState().paletteOpen).toBe(true);
  });

  it('keeps single-key shortcuts on by default for the rail and map views', async () => {
    const { user } = await shell();
    await user.keyboard('[[');
    expect(useShellStore.getState().railCollapsed).toBe(true);
    await user.keyboard('m');
    expect(useGlobeStore.getState().mode).toBe('map');
    await user.keyboard('g');
    expect(useGlobeStore.getState().mode).toBe('globe');
  });

  it('never fires while typing in a field or an editable region', async () => {
    const { user } = await shell();
    const input = document.createElement('input');
    const editable = document.createElement('div');
    editable.setAttribute('contenteditable', '');
    document.body.append(input, editable);
    input.focus();
    await user.keyboard('?m');
    expect(input).toHaveValue('?m');
    fireEvent.keyDown(editable, { key: '?' });
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeInTheDocument();
    expect(useGlobeStore.getState().mode).toBe('globe');
    input.remove();
    editable.remove();
  });

  it('marks single-key shortcuts as off in the help and links to the setting', async () => {
    usePreferencesStore.setState({ singleKeyShortcuts: false });
    const { user, router } = await shell();
    act(() => usePreferencesStore.getState().openShortcutHelp());
    const dialog = screen.getByRole('dialog', { name: 'Keyboard shortcuts' });
    const offCount = SHORTCUT_GROUPS.flatMap((group) => group.entries).filter(
      (entry) => entry.singleKey,
    ).length;
    expect(within(dialog).getAllByText('Off')).toHaveLength(offCount);
    await user.click(within(dialog).getByRole('link', { name: 'keyboard settings' }));
    expect(router.state.location.pathname).toBe('/settings');
    expect(router.state.location.search).toBe('?section=keyboard');
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeInTheDocument();
  });
});
