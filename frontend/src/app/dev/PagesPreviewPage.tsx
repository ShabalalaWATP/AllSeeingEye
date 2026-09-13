/**
 * Development-only page (registered when import.meta.env.DEV) that frames the
 * Subscriptions, Geolocation and Sources layouts inside the shell chrome so they can
 * be inspected without an account. Data-backed parts render their fixture or their
 * error state; nothing here reaches the API with a credential.
 */
import { useSyncExternalStore } from 'react';

import { LeftRail } from '@/app/shell/LeftRail';
import { TopBar } from '@/app/shell/TopBar';
import RecurringResearchPage from '@/features/reports/RecurringResearchPage';
import PhotoResearchPage from '@/features/research/PhotoResearchPage';
import { ConnectionBadge } from '@/features/sources/ConnectionBadge';
import { PlatformConnections } from '@/features/sources/PlatformConnections';
import { SourceCatalogueRow } from '@/features/sources/SourceCatalogueRow';
import type { CatalogueSource } from '@/lib/api/sourceContext';
import { platformConnections, sourceContext } from '@/test/fixtures.researchMetadata';

const PAGES = ['subscriptions', 'geolocation', 'sources'] as const;
type Page = (typeof PAGES)[number];

const subscribe = (onChange: () => void) => {
  window.addEventListener('hashchange', onChange);
  return () => window.removeEventListener('hashchange', onChange);
};
const readPage = (): Page => {
  const hash = window.location.hash.replace('#', '');
  return PAGES.find((page) => page === hash) ?? 'subscriptions';
};

const keyed: CatalogueSource = {
  ...sourceContext,
  id: 'aisstream',
  name: 'AISStream: global ship positions',
  category: 'maritime',
  kind: 'websocket',
  requires_key: true,
  connection: {
    state: 'key_missing',
    enabled: true,
    environment_disabled: false,
    active: false,
    requirement: {
      kind: 'api_key',
      satisfied: false,
      origin: 'none',
      setting: 'ASE_AISSTREAM_API_KEY',
      note: 'Set ASE_AISSTREAM_API_KEY on the server to enable global ship positions.',
      optional: false,
    },
    health: null,
    detail: 'Set ASE_AISSTREAM_API_KEY on the server to enable global ship positions.',
  },
};

function SourcesPreview() {
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-6xl space-y-8 pb-24">
        <header className="rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7">
          <p className="mb-2 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
            Collection directory
          </p>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Sources and connections
          </h1>
        </header>
        <ul aria-label="Connection totals" className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {(
            [
              ['Collecting', 41, 'text-good'],
              ['Needs attention', 2, 'text-amber'],
              ['Key or setup missing', 9, 'text-critical'],
              ['On demand', 58, 'text-cyan'],
              ['Switched off', 1, 'text-muted'],
            ] as const
          ).map(([label, value, tone]) => (
            <li key={label} className="rounded-xl border border-line/70 bg-surface/60 p-4">
              <span className="text-[11px] text-muted">{label}</span>
              <span className={`mt-1 block text-2xl font-semibold tracking-tight ${tone}`}>
                {value}
              </span>
            </li>
          ))}
        </ul>
        <section className="rounded-xl border border-amber/40 bg-amber/5 p-4 sm:p-5">
          <h2 className="text-sm font-semibold">Needs attention</h2>
          <ul className="mt-3 divide-y divide-line/60">
            <li className="flex flex-wrap items-center gap-3 py-2 text-sm">
              <ConnectionBadge state="key_missing" />
              <span className="font-medium">{keyed.name}</span>
              <span className="min-w-0 flex-1 text-xs text-muted">
                {keyed.connection.requirement?.note}
              </span>
              <span className="font-mono text-[10px] text-muted">ASE_AISSTREAM_API_KEY</span>
            </li>
          </ul>
        </section>
        <PlatformConnections
          data={platformConnections}
          loading={false}
          error={null}
          onRetry={() => undefined}
        />
        <ul className="divide-y divide-line">
          <SourceCatalogueRow source={sourceContext} />
          <SourceCatalogueRow source={keyed} />
        </ul>
      </div>
    </section>
  );
}

export default function PagesPreviewPage() {
  const page = useSyncExternalStore(subscribe, readPage, (): Page => 'subscriptions');
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="relative min-h-0 flex-1">
          {page === 'subscriptions' && <RecurringResearchPage />}
          {page === 'geolocation' && <PhotoResearchPage />}
          {page === 'sources' && <SourcesPreview />}
        </main>
      </div>
    </div>
  );
}
