/** Curated public widget symbols, never user-controlled URLs or app/report context. */
export type MarketRegion = 'WORLD' | 'GB' | 'US' | 'RU' | 'CN' | 'IR';

export interface MarketInstrument {
  symbol: string;
  name: string;
  kind: 'Index' | 'Stock' | 'Currency' | 'Commodity CFD' | 'Index CFD';
  timing: string;
  explanation: string;
}

const instruments: Readonly<Record<string, MarketInstrument>> = {
  spx: {
    symbol: 'FOREXCOM:SPXUSD',
    name: 'US 500',
    kind: 'Index CFD',
    timing: 'Streaming provider quote',
    explanation:
      'FOREX.com’s US 500 contract, a proxy for large US shares rather than the official S&P index feed.',
  },
  apple: {
    symbol: 'NASDAQ:AAPL',
    name: 'Apple',
    kind: 'Stock',
    timing: 'Delayed stock data',
    explanation: 'US shares, displayed using the provider’s Cboe One feed.',
  },
  microsoft: {
    symbol: 'NASDAQ:MSFT',
    name: 'Microsoft',
    kind: 'Stock',
    timing: 'Delayed stock data',
    explanation: 'US shares, displayed using the provider’s Cboe One feed.',
  },
  uk100: {
    symbol: 'FOREXCOM:UKXGBP',
    name: 'UK 100',
    kind: 'Index CFD',
    timing: 'Streaming provider quote',
    explanation:
      'FOREX.com’s UK 100 contract, a proxy for large UK shares rather than the official FTSE index feed.',
  },
  sterling: {
    symbol: 'OANDA:GBPUSD',
    name: 'Pound / US dollar',
    kind: 'Currency',
    timing: 'Streaming FX',
    explanation: 'US dollars per pound, quoted by OANDA. FX quotes vary between providers.',
  },
  euro: {
    symbol: 'OANDA:EURUSD',
    name: 'Euro / US dollar',
    kind: 'Currency',
    timing: 'Streaming FX',
    explanation: 'US dollars per euro, quoted by OANDA. FX quotes vary between providers.',
  },
  shanghai: {
    symbol: 'SSE:000001',
    name: 'Shanghai Composite',
    kind: 'Index',
    timing: 'End-of-day data',
    explanation: 'Shanghai-listed shares. This free widget provides end-of-day exchange data.',
  },
  hangSeng: {
    symbol: 'HSI:HSI',
    name: 'Hang Seng',
    kind: 'Index',
    timing: 'End-of-day data',
    explanation: 'Major Hong Kong-listed shares. This is not the same market as mainland China.',
  },
  brent: {
    symbol: 'OANDA:BCOUSD',
    name: 'Brent crude',
    kind: 'Commodity CFD',
    timing: 'Streaming provider quote',
    explanation:
      'OANDA’s Brent oil contract in US dollars, not a physical cargo price or exchange futures feed.',
  },
  gold: {
    symbol: 'OANDA:XAUUSD',
    name: 'Gold / US dollar',
    kind: 'Commodity CFD',
    timing: 'Streaming provider quote',
    explanation: 'OANDA’s gold quote in US dollars per troy ounce.',
  },
};

const regionalKeys: Record<MarketRegion, readonly string[]> = {
  WORLD: ['spx', 'euro', 'sterling', 'brent', 'gold', 'apple', 'microsoft', 'shanghai', 'hangSeng'],
  GB: ['sterling', 'uk100', 'brent', 'gold'],
  US: ['spx', 'apple', 'microsoft', 'euro', 'gold'],
  CN: ['shanghai', 'hangSeng', 'brent', 'gold'],
  RU: [],
  IR: [],
};

export function instrumentsForRegion(region: MarketRegion): readonly MarketInstrument[] {
  return regionalKeys[region].flatMap((key) => instruments[key] ?? []);
}

function approvedInstrument(symbol: string): MarketInstrument {
  const instrument = Object.values(instruments).find((item) => item.symbol === symbol);
  if (!instrument) throw new Error('Unknown market instrument');
  return instrument;
}

export const MARKET_FRAME_ORIGIN = 'https://www.tradingview-widget.com';

/** The iframe URL matches the official advanced-chart embed observed in widget docs. */
export function marketFrameUrl(symbol: string, theme: 'light' | 'dark'): string {
  const instrument = approvedInstrument(symbol);
  const settings = {
    symbol: instrument.symbol,
    interval: 'D',
    theme,
    style: '3',
    autosize: true,
    width: '100%',
    height: '100%',
    timezone: 'Etc/UTC',
    locale: 'en',
    allow_symbol_change: false,
    hide_side_toolbar: true,
    hide_top_toolbar: false,
    hide_legend: false,
    hide_volume: false,
    save_image: false,
    withdateranges: true,
    details: false,
    hotlist: false,
    calendar: false,
    support_host: 'https://www.tradingview.com',
  };
  return `${MARKET_FRAME_ORIGIN}/embed-widget/advanced-chart/?locale=en#${encodeURIComponent(JSON.stringify(settings))}`;
}

export function marketProviderUrl(symbol: string): string {
  return `https://www.tradingview.com/chart/?symbol=${encodeURIComponent(approvedInstrument(symbol).symbol)}`;
}
