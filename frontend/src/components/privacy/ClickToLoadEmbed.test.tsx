import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { embedProviderIds } from '@/lib/embedProviders';
import { EMBED_CONSENT_KEY, useEmbedConsentStore } from '@/stores/embedConsent';
import { expectNoAxeViolations } from '@/test/axe';
import { plainUser, tokenFor } from '@/test/fixtures';
import { ClickToLoadEmbed } from './ClickToLoadEmbed';
import { EmbedPrivacyPreferences } from './EmbedPrivacyPreferences';

beforeEach(() => {
  localStorage.clear();
  for (const provider of embedProviderIds) useEmbedConsentStore.getState().forget(provider);
  useEmbedConsentStore.getState().resetSession();
});

function Embed() {
  return (
    <ClickToLoadEmbed provider="tradingview" content="chart">
      {() => <iframe title="Test chart" src="https://www.tradingview-widget.com/test" />}
    </ClickToLoadEmbed>
  );
}

async function load(remember = false, persist = false) {
  if (remember) await userEvent.click(screen.getByRole('checkbox', { name: /^Remember/ }));
  if (persist) await userEvent.click(screen.getByRole('checkbox', { name: /^Also save/ }));
  await userEvent.click(screen.getByRole('button', { name: 'Load chart from TradingView' }));
}

it('discloses the provider without mounting an embed, and grants only this instance by default', async () => {
  const view = render(<Embed />);
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(screen.getByText(/receives your IP address/)).toHaveTextContent('may set cookies');
  expect(screen.getByRole('link', { name: 'TradingView privacy policy' })).toHaveAttribute(
    'href',
    'https://www.tradingview.com/privacy-policy/',
  );
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(localStorage.getItem(EMBED_CONSENT_KEY)).toBeNull();
  await load();
  expect(screen.getByTitle('Test chart')).toBeInTheDocument();
  expect(localStorage.getItem(EMBED_CONSENT_KEY)).toBeNull();
  view.unmount();
  render(<Embed />);
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
});

it('remembers across component remounts in memory and forgets on an account change', async () => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  const view = render(<Embed />);
  await load(true);
  view.unmount();
  render(<Embed />);
  expect(screen.getByTitle('Test chart')).toBeInTheDocument();
  expect(localStorage.getItem(EMBED_CONSENT_KEY)).toBeNull();
  act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
  expect(screen.getByTitle('Test chart')).toBeInTheDocument();
  act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'other' })));
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
});

it('persists only an explicitly checked browser choice and withdrawal stops every mounted embed', async () => {
  const view = render(<Embed />);
  await load(true, true);
  expect(JSON.parse(localStorage.getItem(EMBED_CONSENT_KEY)!)).toEqual({
    version: 1,
    providers: ['tradingview'],
  });
  view.unmount();
  act(() => useEmbedConsentStore.getState().resetSession());
  render(
    <>
      <Embed />
      <Embed />
      <EmbedPrivacyPreferences />
    </>,
  );
  expect(screen.getAllByTitle('Test chart')).toHaveLength(2);
  await userEvent.click(
    within(screen.getByRole('region', { name: 'External media' })).getByRole('button', {
      name: 'Forget TradingView choice',
    }),
  );
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(localStorage.getItem(EMBED_CONSENT_KEY)).toBeNull();
  expect(screen.getAllByRole('button', { name: 'Load chart from TradingView' })).toHaveLength(2);
});

it('keeps persistence unchecked after disabling session remembering', async () => {
  render(<Embed />);
  await userEvent.click(screen.getByRole('checkbox', { name: /^Remember/ }));
  await userEvent.click(screen.getByRole('checkbox', { name: /^Also save/ }));
  await userEvent.click(screen.getByRole('checkbox', { name: /^Remember/ }));
  await load(true);
  expect(localStorage.getItem(EMBED_CONSENT_KEY)).toBeNull();
});

it('fails closed for corrupt or unknown saved providers', () => {
  for (const raw of [
    '{',
    'null',
    '{}',
    '{"version":2,"providers":["tradingview"]}',
    '{"version":1,"providers":"tradingview"}',
    '{"version":1,"providers":["tradingview","unknown"]}',
  ]) {
    localStorage.setItem(EMBED_CONSENT_KEY, raw);
    useEmbedConsentStore.getState().resetSession();
    expect(useEmbedConsentStore.getState().choices.tradingview).toBeNull();
  }
});

it('reports blocked persistence and retains only the session choice', async () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('blocked');
  });
  render(<Embed />);
  await load(true, true);
  expect(screen.getByTitle('Test chart')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('session only');
  expect(useEmbedConsentStore.getState().choices.tradingview).toBe('session');
});

it('blocks immediately but reports if a saved choice cannot be removed', async () => {
  render(<Embed />);
  await load(true, true);
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
    throw new Error('blocked');
  });
  await userEvent.click(screen.getByRole('button', { name: 'Forget TradingView choice' }));
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('could not clear the saved choice');
  act(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('could not clear the saved choice');
  act(() => {
    window.dispatchEvent(new StorageEvent('storage', { key: EMBED_CONSENT_KEY }));
  });
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
});

it('fails safely if storage cannot be read', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('blocked');
  });
  useEmbedConsentStore.getState().resetSession();
  render(<Embed />);
  await load(true, true);
  expect(screen.getByRole('alert')).toHaveTextContent('session only');
  await userEvent.click(screen.getByRole('button', { name: 'Forget TradingView choice' }));
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('could not clear');
});

it('applies withdrawal from another tab and preserves unrelated session choices', async () => {
  render(<Embed />);
  await load(true, true);
  act(() => useEmbedConsentStore.getState().remember('youtube', false));
  act(() => {
    localStorage.removeItem(EMBED_CONSENT_KEY);
    window.dispatchEvent(new StorageEvent('storage', { key: EMBED_CONSENT_KEY }));
  });
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(useEmbedConsentStore.getState().choices.youtube).toBe('session');
});

it('withdraws a one-off grant and can be operated using the keyboard', async () => {
  render(
    <main>
      <h1>External chart</h1>
      <Embed />
    </main>,
  );
  await expectNoAxeViolations();
  screen.getByRole('button', { name: 'Load chart from TradingView' }).focus();
  await userEvent.keyboard('{Enter}');
  expect(screen.getByTitle('Test chart')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Block TradingView' })).toHaveFocus();
  await userEvent.click(screen.getByRole('button', { name: 'Block TradingView' }));
  expect(screen.queryByTitle('Test chart')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Load chart from TradingView' })).toHaveFocus();
  await expectNoAxeViolations();
});

it('keeps consent separate for each provider and passes whether this instance was explicitly loaded', async () => {
  const view = render(
    <ClickToLoadEmbed provider="youtube" content="video">
      {(loaded) => <p>Explicit: {String(loaded)}</p>}
    </ClickToLoadEmbed>,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Load video from YouTube' }));
  expect(screen.getByText('Explicit: true')).toBeInTheDocument();
  view.rerender(
    <ClickToLoadEmbed provider="ipcamlive" content="video">
      {() => <p>IPCamLive frame</p>}
    </ClickToLoadEmbed>,
  );
  expect(screen.queryByText('IPCamLive frame')).not.toBeInTheDocument();
});
