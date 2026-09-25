/**
 * Development-only page (registered when import.meta.env.DEV) that frames the plain
 * English economy panels against fixtures, so the layout can be inspected without an
 * account. Nothing here reaches the API with a credential.
 */
import { useSyncExternalStore } from 'react';

import { CountryEconomy } from '@/features/economy/CountryEconomy';
import { regionExplainer } from '@/features/economy/explainerModel';
import { WorldExplainer } from '@/features/economy/WorldExplainer';
import type { EconomyExplainerState } from '@/features/economy/useEconomyExplainer';
import { economyDepthSnapshot } from '@/test/fixtures.economyDepth';
import { economyExplainer, explainerState } from '@/test/fixtures.economyExplainer';

const VIEWS = ['ready', 'stale', 'empty', 'unavailable', 'validation_failed', 'admin'] as const;
type View = (typeof VIEWS)[number];

const subscribe = (onChange: () => void) => {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
};
const readView = (): View => {
  const hash = window.location.hash.replace('#', '');
  return VIEWS.find((view) => view === hash) ?? 'ready';
};

const REASONS: Record<string, string | null> = {
  stale: null,
  empty:
    'No plain-English summary has been written yet. One is written from the figures on this page at most once a day.',
  unavailable:
    'The AI usage allowance is spent, so no written summary was produced. The figures on this page are unaffected.',
  validation_failed:
    'A written summary was produced but it failed the automatic checks against the figures, so it was discarded. The figures on this page are the source of truth.',
};

function state(view: View): EconomyExplainerState {
  const data =
    view === 'ready' || view === 'admin'
      ? economyExplainer
      : explainerState(view, REASONS[view] ?? null);
  return {
    data,
    loading: false,
    error: null,
    refreshing: false,
    refreshError: null,
    isAdmin: view === 'admin',
    reload: () => Promise.resolve(),
    forceRefresh: () => Promise.resolve(),
  };
}

export default function EconomyPreviewPage() {
  const view = useSyncExternalStore(subscribe, readView, (): View => 'ready');
  const explainer = state(view);
  const region = economyDepthSnapshot.regions.find((item) => item.id === 'GB');
  return (
    <div className="min-h-dvh bg-ground text-text">
      <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
        <div className="mx-auto max-w-[1500px] space-y-8 pb-24">
          <header>
            <p className="mb-2 font-mono text-2xs tracking-[0.22em] text-ember uppercase">
              Economic intelligence
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">Economy</h1>
            <p className="mt-2 text-sm text-muted">
              Fixture preview: {view}. Change the hash to {VIEWS.join(', ')}.
            </p>
          </header>
          <WorldExplainer state={explainer} />
          <CountryEconomy region={region} explainer={regionExplainer(explainer.data, 'GB')} />
        </div>
      </section>
    </div>
  );
}
