import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';
import { setVisibility } from '@/test/env';
import { plainUser, tokenFor } from '@/test/fixtures';
import { defaultProfile } from '@/test/handlers.profile';

import { MarketWorkspace } from './MarketWorkspace';
import {
  instrumentsForRegion,
  MARKET_FRAME_ORIGIN,
  marketFrameUrl,
  marketProviderUrl,
} from './marketInstruments';

function signIn() {
  useAuthStore.getState().setSession(tokenFor(plainUser));
}

function chart() {
  return document.querySelector('iframe');
}

describe('market workspace', () => {
  it('automatically loads the selected chart and lets the user stop and resume it', async () => {
    signIn();
    render(<MarketWorkspace region="US" />);
    expect(screen.getByTitle('US 500 market chart')).toBeInTheDocument();
    expect(chart()).toHaveAttribute('loading', 'eager');
    expect(document.querySelector('script[src]')).toBeNull();
    await userEvent.click(screen.getByText('Chart provider, timing & privacy'));
    expect(screen.getByText(/receives your IP address and the selected public/)).toBeVisible();
    expect(chart()).toHaveAttribute('referrerpolicy', 'no-referrer');
    expect(chart()).toHaveAttribute(
      'sandbox',
      'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox',
    );
    expect(chart()?.src).toMatch(
      /^https:\/\/www\.tradingview-widget\.com\/embed-widget\/advanced-chart\//,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Stop charts' }));
    expect(chart()).toBeNull();
    expect(screen.getByText('Market charts paused')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Resume charts' }));
    expect(screen.getByTitle('US 500 market chart')).toBeInTheDocument();
  });

  it('switches curated instruments and regions with at most one mounted chart', async () => {
    signIn();
    const view = render(<MarketWorkspace region="US" />);
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Market instrument' }),
      'NASDAQ:AAPL',
    );
    expect(screen.getByTitle('Apple market chart')).toBeInTheDocument();
    expect(screen.getByText('Delayed stock data')).toBeInTheDocument();
    view.rerender(<MarketWorkspace region="CN" />);
    expect(screen.getByTitle('Shanghai Composite market chart')).toBeInTheDocument();
    expect(screen.getByText('End-of-day data')).toBeInTheDocument();
    expect(document.querySelectorAll('iframe')).toHaveLength(1);
    view.unmount();
    expect(chart()).toBeNull();
  });

  it('unmounts hidden-tab charts and resumes unless the user stopped charts', async () => {
    signIn();
    render(<MarketWorkspace region="GB" />);
    act(() => setVisibility('hidden'));
    expect(chart()).toBeNull();
    expect(screen.getByText('Charts paused while this tab is hidden')).toBeInTheDocument();
    act(() => setVisibility('visible'));
    expect(screen.getByTitle('Pound / US dollar market chart')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Stop charts' }));
    act(() => setVisibility('hidden'));
    act(() => setVisibility('visible'));
    expect(chart()).toBeNull();
  });

  it('does not connect while initially hidden and loads when the tab becomes visible', () => {
    signIn();
    setVisibility('hidden');
    render(<MarketWorkspace region="GB" />);
    expect(chart()).toBeNull();
    act(() => setVisibility('visible'));
    expect(screen.getByTitle('Pound / US dollar market chart')).toBeInTheDocument();
  });

  it('resets selections and pauses on identity changes and removes inactive sessions', async () => {
    signIn();
    render(<MarketWorkspace region="WORLD" />);
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Market instrument' }),
      'NASDAQ:AAPL',
    );
    expect(screen.getByTitle('Apple market chart')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Stop charts' }));
    expect(chart()).toBeNull();
    act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: 'another-user' })));
    expect(screen.getByTitle('US 500 market chart')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Resume charts' })).not.toBeInTheDocument();
    act(() => useAuthStore.setState({ user: { ...plainUser, is_active: false } }));
    expect(chart()).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Prices & charts' })).not.toBeInTheDocument();
  });

  it('never mounts the workspace for an anonymous account', () => {
    render(<MarketWorkspace region="WORLD" />);
    expect(screen.queryByRole('heading', { name: 'Prices & charts' })).not.toBeInTheDocument();
  });

  it.each(['RU', 'IR'] as const)(
    'explains the %s exchange coverage gap without substitute quotes',
    (region) => {
      signIn();
      render(<MarketWorkspace region={region} />);
      expect(screen.getByText(/No verified .* feed is available/)).toBeInTheDocument();
      expect(chart()).toBeNull();
      expect(screen.queryByRole('button', { name: 'Resume charts' })).not.toBeInTheDocument();
      expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    },
  );

  it('uses only the signed-in user’s chart theme', () => {
    signIn();
    useProfileStore.setState({
      owner: 'someone-else',
      profile: { ...defaultProfile, appearance_theme: 'light' },
    });
    render(<MarketWorkspace region="GB" />);
    expect(decodeURIComponent(chart()!.src)).toContain('"theme":"dark"');
    act(() =>
      useProfileStore.setState({
        owner: plainUser.id,
        profile: { ...defaultProfile, appearance_theme: 'light' },
      }),
    );
    expect(decodeURIComponent(chart()!.src)).toContain('"theme":"light"');
  });

  it('offers a manual reload and provider fallback without claiming third-party health', async () => {
    signIn();
    render(<MarketWorkspace region="GB" />);
    const previousFrame = chart();
    await userEvent.click(screen.getByRole('button', { name: 'Reload chart' }));
    expect(chart()).not.toBe(previousFrame);
    expect(screen.getByText(/If the chart cannot load/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /chart by TradingView/ })).toHaveAttribute(
      'rel',
      'noopener noreferrer',
    );
  });
});

describe('market symbol boundary', () => {
  it.each(['https://evil.example/AAPL', 'NASDAQ:AAPL&token=private', '', 'MOEX:IMOEX'])(
    'refuses unapproved symbols: %s',
    (symbol) => {
      expect(() => marketFrameUrl(symbol, 'dark')).toThrow('Unknown market instrument');
      expect(() => marketProviderUrl(symbol)).toThrow('Unknown market instrument');
    },
  );

  it('encodes only approved chart settings in an isolated provider URL', () => {
    const url = new URL(marketFrameUrl('NASDAQ:AAPL', 'dark'));
    expect(url.origin).toBe(MARKET_FRAME_ORIGIN);
    expect(url.search).toBe('?locale=en');
    const settings = JSON.parse(decodeURIComponent(url.hash.slice(1)));
    expect(settings).toMatchObject({
      symbol: 'NASDAQ:AAPL',
      allow_symbol_change: false,
      save_image: false,
    });
    expect(settings).not.toHaveProperty('page-uri');
    expect(settings).not.toHaveProperty('utm_source');
    expect(marketProviderUrl('NASDAQ:AAPL')).toBe(
      'https://www.tradingview.com/chart/?symbol=NASDAQ%3AAAPL',
    );
    expect(instrumentsForRegion('GB').some((item) => item.kind === 'Index CFD')).toBe(true);
    expect(instrumentsForRegion('RU')).toEqual([]);
  });
});
