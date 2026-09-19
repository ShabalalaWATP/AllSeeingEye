import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { useShellStore } from '@/stores/shell';

import { commandTargets, matchTargets } from './commandTargets';

// jsdom has no native dialog top layer. Real browser checks cover its focus trap.
beforeAll(() => {
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

afterAll(() => {
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
});

afterEach(() => {
  useShellStore.setState({ paletteOpen: false });
});

it('opens from the rail, jumps to a tracker and returns focus to its trigger', async () => {
  const { user, router } = renderApp('/research/saved', 'user');
  const trigger = await screen.findByRole('button', { name: /Find anything/ });
  await user.click(trigger);
  const palette = await screen.findByRole('dialog', { name: 'Find anything' });
  const search = within(palette).getByRole('combobox');
  expect(search).toHaveFocus();
  await user.type(search, 'maritime');
  const results = within(palette).getByRole('listbox', { name: 'Results' });
  await user.click(within(results).getAllByRole('option')[0]!);
  await waitFor(() => {
    expect(router.state.location.pathname).toBe('/trackers/maritime');
  });
  expect(screen.queryByRole('dialog', { name: 'Find anything' })).not.toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /Find anything/ })).toHaveFocus();
  });
});

it('opens with the keyboard and moves through results with the arrow keys', async () => {
  const { user, router } = renderApp('/research/saved', 'user');
  await screen.findByRole('button', { name: /Find anything/ });
  await user.keyboard('{Control>}k{/Control}');
  const palette = await screen.findByRole('dialog', { name: 'Find anything' });
  await user.type(within(palette).getByRole('combobox'), 'cameras');
  const options = within(palette).getAllByRole('option');
  expect(options[0]).toHaveAttribute('aria-selected', 'true');
  await user.keyboard('{ArrowDown}');
  expect(within(palette).getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true');
  await user.keyboard('{ArrowUp}{Enter}');
  await waitFor(() => {
    expect(router.state.location.search).toContain('panel=CCTV');
  });
});

it('closes on dismissal without navigating', async () => {
  const { user, router } = renderApp('/research/saved', 'user');
  await user.click(await screen.findByRole('button', { name: /Find anything/ }));
  // jsdom does not raise the native Escape cancel, so dispatch what the browser would.
  fireEvent(
    await screen.findByRole('dialog', { name: 'Find anything' }),
    new Event('cancel', { cancelable: true }),
  );
  await waitFor(() => {
    expect(screen.queryByRole('dialog', { name: 'Find anything' })).not.toBeInTheDocument();
  });
  expect(router.state.location.pathname).toBe('/research/saved');
  await user.click(screen.getByRole('button', { name: /Find anything/ }));
  await user.click(await screen.findByRole('button', { name: 'Close search' }));
  await waitFor(() => {
    expect(screen.queryByRole('dialog', { name: 'Find anything' })).not.toBeInTheDocument();
  });
});

it('reaches pages, trackers and map layers, and never administration', () => {
  const targets = commandTargets();
  const routes = targets.map((target) => target.to);
  // Alerts and rules are reached from Settings now, not from the primary rail.
  expect(routes).not.toContain('/warning');
  expect(routes).toContain('/trackers/space');
  expect(routes).toContain('/?panel=CCTV');
  // The catalogue is an administrator's page now, so an analyst cannot jump to it.
  expect(routes.some((route) => route.startsWith('/admin'))).toBe(false);
  expect(new Set(targets.map((target) => target.id)).size).toBe(targets.length);
});

it('offers the source catalogue by family only to an administrator', () => {
  const routes = commandTargets({ admin: true }).map((target) => target.to);
  expect(routes).toContain('/admin/catalogue?family=map_layer');
  expect(commandTargets().some((target) => target.group === 'Sources')).toBe(false);
});

it('ranks a label match above a description match and needs every term', () => {
  // The catalogue families are an administrator's entries, and one of them carries
  // the two-term case this ranks.
  const targets = commandTargets({ admin: true });
  expect(matchTargets(targets, 'teams')[0]?.label).toBe('Teams');
  expect(matchTargets(targets, 'ukraine dataset').map((target) => target.label)).toEqual([
    'Ukraine tracker datasets',
  ]);
  expect(matchTargets(targets, 'zzzz')).toHaveLength(0);
  expect(matchTargets(targets, '   ', 3)).toHaveLength(3);
});
