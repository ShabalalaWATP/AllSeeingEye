import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchEconomy, fetchEconomyNews } from '@/lib/api/economy';
import { describeError } from '@/lib/api/errors';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useAuthStore } from '@/stores/auth';
import { REGIONS } from './economyPresentation';
import { EconomyNewsPanel } from './EconomyNewsPanel';
import { CountryEconomy } from './CountryEconomy';
import { CurrencyContext } from './CurrencyContext';
import { MarketWorkspace } from './MarketWorkspace';
import { EconomyBriefing } from './EconomyBriefing';
import { CountryComparison } from './CountryComparison';
import { CurrencyAnalysis } from './CurrencyAnalysis';
import { parseEconomyDays } from '@/lib/api/economyBriefing';
import { EconomyPeriodPicker } from './EconomyPeriodPicker';
import { useEconomyBriefing } from './useEconomyBriefing';
import { useEconomyExplainer } from './useEconomyExplainer';
import { WorldExplainer } from './WorldExplainer';
import { regionExplainer } from './explainerModel';

export default function EconomyPage() {
  const [params, setParams] = useSearchParams();
  const days = parseEconomyDays(params.get('days'));
  const focus = REGIONS.find((item) => item.id === params.get('region')) ?? REGIONS[0];
  const data = useScopedResource(fetchEconomy);
  const loadNews = useCallback(() => fetchEconomyNews(days), [days]);
  const news = useScopedResource(loadNews);
  const currentNews = news.data?.window_hours === days * 24 ? news.data : null;
  const briefingState = useEconomyBriefing(days);
  const explainerState = useEconomyExplainer();
  const worldExplainer = regionExplainer(explainerState.data, 'WORLD');
  const focusExplainer = regionExplainer(explainerState.data, focus.id);
  const [refreshing, setRefreshing] = useState(false);
  const owner = useAuthStore((state) => state.user?.id);
  const refreshData = data.refresh;
  const refreshNews = news.refresh;
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') void Promise.all([refreshData(), refreshNews()]);
    }, 300_000);
    return () => clearInterval(timer);
  }, [refreshData, refreshNews]);
  const refresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([data.reload(), news.reload()]);
    } finally {
      setRefreshing(false);
    }
  };
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-[1500px] space-y-8 pb-24">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.22em] text-ember">
              Economic intelligence
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">Economy</h1>
            <p className="mt-2 text-sm text-muted">
              Markets, economic signals and the stories behind them.
            </p>
          </div>
          <Button variant="secondary" busy={refreshing} onClick={() => void refresh()}>
            Refresh news & indicators
          </Button>
        </header>
        <EconomyPeriodPicker
          days={days}
          onChange={(value) =>
            setParams((previous) => {
              previous.set('days', String(value));
              return previous;
            })
          }
        />
        <WorldExplainer state={explainerState} />
        <EconomyNewsPanel
          items={currentNews?.items ?? []}
          loading={news.loading}
          error={news.error ? describeError(news.error) : null}
          coverage={currentNews?.coverage_note}
          days={days}
          asOf={currentNews?.as_of}
          report={briefingState.report}
          briefing={briefingState.briefing}
          explainerLeads={worldExplainer.section !== null}
          region="WORLD"
          onRetry={() => void news.reload()}
        />
        <nav
          aria-label="Economy country focus"
          className="flex flex-wrap gap-1 border-y border-line py-2"
        >
          {REGIONS.map((region) => (
            <button
              key={region.id}
              type="button"
              aria-pressed={focus.id === region.id}
              onClick={() =>
                setParams((previous) => {
                  if (region.id === 'WORLD') previous.delete('region');
                  else previous.set('region', region.id);
                  return previous;
                })
              }
              className={`min-h-11 rounded-md px-4 text-sm transition-colors ${focus.id === region.id ? 'bg-surface-2 text-ember' : 'text-muted hover:bg-surface-2 hover:text-text'}`}
            >
              {region.short}
            </button>
          ))}
        </nav>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{focus.name} focus</h2>
          <p className="mt-2 max-w-3xl text-sm text-muted">{focus.detail}</p>
        </div>
        <nav
          aria-label="Economic analysis sections"
          className="flex flex-wrap gap-x-6 gap-y-3 text-xs text-muted"
        >
          <a className="hover:text-ember" href="#economy-markets">
            Markets
          </a>
          <a className="hover:text-ember" href="#economy-comparison">
            Compare countries
          </a>
          <a className="hover:text-ember" href="#economy-country">
            Country profile
          </a>
          <a className="hover:text-ember" href="#economy-analysis">
            Economic summary
          </a>
          <a className="hover:text-ember" href="#economy-currencies">
            Currencies
          </a>
        </nav>
        <div id="economy-markets">
          <MarketWorkspace key={owner} region={focus.id} />
        </div>
        {data.loading && !data.data && <LoadingNote label="Loading official economic indicators" />}
        {data.error && (
          <Alert tone="error">
            {describeError(data.error)}{' '}
            <Button variant="ghost" onClick={() => void data.reload()}>
              Retry indicators
            </Button>
          </Alert>
        )}
        {data.data && (
          <div id="economy-comparison">
            <CountryComparison regions={data.data.regions} focus={focus.id} />
          </div>
        )}
        {data.data && (
          <div id="economy-country">
            <CountryEconomy
              key={focus.id}
              region={data.data.regions.find((region) => region.id === focus.id)}
              explainer={focusExplainer}
            />
          </div>
        )}
        {focus.id !== 'WORLD' && (
          <EconomyNewsPanel
            items={currentNews?.items ?? []}
            loading={news.loading}
            error={news.error ? describeError(news.error) : null}
            region={focus.id}
            days={days}
            asOf={currentNews?.as_of}
            report={briefingState.report}
            briefing={briefingState.briefing}
            explainerLeads={focusExplainer.section !== null}
            onRetry={() => void news.reload()}
          />
        )}
        <div id="economy-analysis">
          <EconomyBriefing days={days} state={briefingState} />
        </div>
        {data.data && (
          <div id="economy-currencies">
            <CurrencyAnalysis items={data.data.fx} />
          </div>
        )}
        {data.data && <CurrencyContext items={data.data.fx} />}
        <details className="border-t border-line pt-5 text-xs leading-6 text-muted">
          <summary className="w-fit cursor-pointer font-medium hover:text-text">
            How to read this page
          </summary>
          <p className="mt-3 max-w-4xl">
            Markets and economies move on different timescales. Stock prices are not measures of
            national wellbeing. Annual indicators describe past periods and can be revised. Daily
            currency reference rates are not executable prices. Missing data means coverage is
            unavailable, not that the value is zero.
          </p>
          <p className="mt-2 max-w-4xl">
            AI analysis cites collected economic reporting and available official indicators. It
            cannot read the external market chart or verify a trade. Regional news tags describe the
            subject or publisher remit, not a verified incident location.
          </p>
        </details>
      </div>
    </section>
  );
}
