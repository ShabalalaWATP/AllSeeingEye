import { useState } from 'react';

import { usePageVisible } from '@/components/brand/useMotionPreferences';
import { Button } from '@/components/ui/Button';
import { SelectField } from '@/components/ui/Field';
import { useAuthStore } from '@/stores/auth';
import { useProfileStore } from '@/stores/profile';

import { instrumentsForRegion, marketFrameUrl, marketProviderUrl } from './marketInstruments';
import type { MarketInstrument, MarketRegion } from './marketInstruments';

/** Session-keyed consent prevents another account inheriting an external connection. */
export function MarketWorkspace({ region }: { region: MarketRegion }) {
  const owner = useAuthStore((state) =>
    state.status === 'authenticated' && state.user?.is_active ? state.user.id : null,
  );
  const lightTheme = useProfileStore(
    (state) => state.owner === owner && state.profile?.appearance_theme === 'light',
  );
  if (!owner) return null;
  return <MarketSession key={owner} region={region} theme={lightTheme ? 'light' : 'dark'} />;
}

function MarketSession({ region, theme }: { region: MarketRegion; theme: 'light' | 'dark' }) {
  const [enabled, setEnabled] = useState(false);
  const [selected, setSelected] = useState('');
  const visible = usePageVisible();
  const choices = instrumentsForRegion(region);
  const instrument = choices.find((item) => item.symbol === selected) ?? choices[0];
  const running = enabled && visible && instrument !== undefined;

  return (
    <section
      aria-labelledby="market-workspace-heading"
      className="min-w-0 border-t border-line py-6"
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 font-mono text-xs tracking-wider text-muted">MARKET WORKSPACE</p>
          <h2 id="market-workspace-heading" className="text-xl font-semibold text-text">
            Prices & charts
          </h2>
        </div>
        {instrument && (
          <div className="flex w-full flex-wrap items-end gap-3 sm:w-auto">
            <div className="min-w-0 flex-1 sm:w-64">
              <SelectField
                label="Market instrument"
                value={instrument.symbol}
                onChange={(event) => setSelected(event.target.value)}
                options={choices.map((item) => ({ value: item.symbol, label: item.name }))}
              />
            </div>
            {enabled && (
              <Button variant="secondary" onClick={() => setEnabled(false)}>
                Stop charts
              </Button>
            )}
          </div>
        )}
      </div>
      {!instrument ? (
        <div className="border-l-2 border-ember/50 py-3 pl-4">
          <h3 className="font-medium text-text">
            {region === 'RU' ? 'Russian' : 'Iranian'} exchange feed unavailable
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
            No verified {region === 'RU' ? 'Moscow Exchange' : 'Tehran exchange'} feed is available
            in this market widget. Use this region’s economic indicators, reporting and daily
            analysis below. Global oil, currencies and other markets are available under Worldwide.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs">
            <span className="font-mono text-ember">{instrument.kind}</span>
            <span className="text-text">{instrument.timing}</span>
            <span className="text-muted">Market hours and provider availability apply</span>
          </div>
          {running ? (
            <ProviderChart
              key={`${instrument.symbol}:${theme}`}
              instrument={instrument}
              theme={theme}
            />
          ) : (
            <div className="flex min-h-64 flex-col items-start justify-center gap-4 border-y border-line bg-surface/40 px-4 py-8 sm:px-8">
              <div>
                <h3 className="text-lg font-medium text-text">
                  {enabled ? 'Charts paused while this tab is hidden' : 'Explore market movements'}
                </h3>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
                  Load interactive TradingView charts for {instrument.name}. Your browser connects
                  directly to TradingView, which receives your IP address and the selected public
                  symbol. Your research and account details are not sent.
                </p>
              </div>
              {!enabled && <Button onClick={() => setEnabled(true)}>Load market charts</Button>}
            </div>
          )}
          <p className="mt-3 text-sm leading-relaxed text-muted">{instrument.explanation}</p>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
            <a
              className="text-ember underline underline-offset-4"
              href={marketProviderUrl(instrument.symbol)}
              target="_blank"
              rel="noopener noreferrer"
            >
              {instrument.name} chart by TradingView ↗
            </a>
            <span>Chart prices are separate from the cited AI briefing.</span>
          </div>
        </>
      )}
    </section>
  );
}

function ProviderChart({
  instrument,
  theme,
}: {
  instrument: MarketInstrument;
  theme: 'light' | 'dark';
}) {
  const [attempt, setAttempt] = useState(0);
  return (
    <div className="border-y border-line">
      <iframe
        key={attempt}
        title={`${instrument.name} market chart`}
        src={marketFrameUrl(instrument.symbol, theme)}
        className="h-[420px] w-full border-0 sm:h-[500px]"
        sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
        referrerPolicy="no-referrer"
        loading="lazy"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-3 py-2">
        <p className="max-w-2xl text-xs text-muted">
          If the chart cannot load, try again or open the provider link below. Exchange permissions
          can change; stock and index prices may be delayed or end-of-day.
        </p>
        <Button variant="ghost" onClick={() => setAttempt((current) => current + 1)}>
          Reload chart
        </Button>
      </div>
    </div>
  );
}
