import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { CYBER_PERIODS, parseCyberDays } from '@/lib/api/cyber';
import { describeError } from '@/lib/api/errors';
import { CYBER_KIND_LABELS, type CyberKindFilter } from '@/lib/cyber';
import { formatUtc } from '@/lib/format';
import { prepareCyberMap } from '@/stores/cyberFilters';
import { CyberActivity } from './CyberActivity';
import { CyberActors } from './CyberActors';
import { CyberBriefing } from './CyberBriefing';
import { CyberOverview } from './CyberOverview';
import { CyberSourceCoverage } from './CyberSourceCoverage';
import { CyberVulnerabilities } from './CyberVulnerabilities';
import { cyberCountry, filterCyberItems } from './cyberPresentation';
import { useCyberWorkspace } from './useCyberWorkspace';

const TABS = [
  { id: 'activity', label: 'Activity' },
  { id: 'actors', label: 'Threat actors' },
  { id: 'vulnerabilities', label: 'Exploited vulnerabilities' },
  { id: 'briefing', label: 'Intelligence briefing' },
] as const;
type Tab = (typeof TABS)[number]['id'];
const field =
  'min-h-11 rounded-md border border-line bg-surface px-3 text-sm text-text focus:border-ember focus:outline-none';

export default function CyberPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const days = parseCyberDays(params.get('days'));
  const [tab, setTab] = useState<Tab>('activity');
  const [query, setQuery] = useState('');
  const [country, setCountry] = useState('');
  const [kind, setKind] = useState<CyberKindFilter>('all');
  const [actor, setActor] = useState('');
  const [selectedActor, setSelectedActor] = useState('');
  const { snapshot, actors, briefing } = useCyberWorkspace(days);
  const data = snapshot.data;
  const items = useMemo(
    () => filterCyberItems(data?.items ?? [], query, kind, country, actor),
    [data, query, kind, country, actor],
  );
  const vulnerabilities = useMemo(
    () => filterCyberItems(data?.items ?? [], query, 'known_exploited_vulnerability', '', ''),
    [data, query],
  );
  const selectedName = actors.data?.catalogue?.actors.find((item) => item.group_id === actor)?.name;
  const inspectActor = (id: string) => {
    setSelectedActor(id);
    setTab('actors');
  };
  const clear = () => {
    setQuery('');
    setCountry('');
    setKind('all');
    setActor('');
  };
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-[1500px] space-y-7 pb-28">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.22em] text-cyan">
              Cyber intelligence
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">Cyber threat intelligence</h1>
            <p className="mt-2 text-sm leading-6 text-muted">
              Reported campaigns, actor tradecraft and exploitation, with the evidence behind each
              assessment.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={() => void snapshot.reload()}
              busy={snapshot.loading}
            >
              Refresh sources
            </Button>
            <Button
              onClick={() =>
                void navigate(prepareCyberMap({ country: country || null, days, kind, query }))
              }
            >
              Open cyber map
            </Button>
          </div>
        </header>
        <section
          aria-label="Cyber reporting period"
          className="flex flex-wrap items-center justify-between gap-4 border-y border-line py-4"
        >
          <div>
            <h2 className="text-sm font-semibold">Reporting period</h2>
            <p className="mt-1 text-xs leading-5 text-muted">
              Applies to activity and the AI briefing. Actor profiles retain their own reference
              dates.
            </p>
          </div>
          <div
            role="group"
            aria-label="Choose cyber reporting period"
            className="flex gap-1 rounded-lg bg-surface p-1"
          >
            {CYBER_PERIODS.map((period) => (
              <button
                key={period}
                type="button"
                aria-pressed={days === period}
                onClick={() =>
                  setParams((previous) => {
                    previous.set('days', String(period));
                    return previous;
                  })
                }
                className={`min-h-11 min-w-16 rounded-md px-3 text-sm transition-colors ${days === period ? 'bg-ember font-semibold text-ground' : 'text-muted hover:bg-surface-2 hover:text-text'}`}
              >
                {period} Day
              </button>
            ))}
          </div>
        </section>
        {snapshot.loading && !data && <LoadingNote label="Loading cyber activity" />}
        {snapshot.error && (
          <Alert tone="error">
            {describeError(snapshot.error)}{' '}
            <Button variant="ghost" onClick={() => void snapshot.reload()}>
              Retry cyber sources
            </Button>
          </Alert>
        )}
        {data && (
          <>
            <p className="text-xs text-muted">
              Evidence window: {formatUtc(data.period_from)} to {formatUtc(data.period_to)}
            </p>
            <CyberOverview
              data={data}
              onCountry={(value) => {
                setCountry(value);
                setTab('activity');
              }}
              onActor={inspectActor}
            />
          </>
        )}
        <nav
          aria-label="Cyber workspace sections"
          className="flex flex-wrap gap-2 border-b border-line pb-3"
        >
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={tab === item.id}
              onClick={() => setTab(item.id)}
              className={`min-h-11 rounded-md px-4 text-sm font-medium transition-colors ${tab === item.id ? 'bg-surface-2 text-text' : 'text-muted hover:bg-surface hover:text-text'}`}
            >
              {item.label}
              {item.id === 'briefing' &&
                (briefing.briefing?.job.status === 'running' ||
                  briefing.briefing?.job.status === 'queued') && (
                  <span className="ml-2 text-[10px] text-cyan">Preparing</span>
                )}
            </button>
          ))}
        </nav>
        {(tab === 'activity' || tab === 'vulnerabilities') && (
          <section aria-label="Filter cyber reporting" className="space-y-3">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex min-w-48 flex-1 flex-col gap-2 text-xs text-muted">
                Search returned reports
                <input
                  type="search"
                  value={query}
                  maxLength={120}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Actor, CVE, product or keyword"
                  className={field}
                />
              </label>
              {tab === 'activity' && (
                <>
                  <label className="flex flex-col gap-2 text-xs text-muted">
                    Evidence type
                    <select
                      value={kind}
                      onChange={(event) => setKind(event.target.value as CyberKindFilter)}
                      className={field}
                    >
                      <option value="all">All cyber reporting</option>
                      {Object.entries(CYBER_KIND_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex flex-col gap-2 text-xs text-muted">
                    Country context
                    <select
                      value={country}
                      onChange={(event) => setCountry(event.target.value)}
                      className={field}
                    >
                      <option value="">All locations</option>
                      {data?.top_countries.map((item) => (
                        <option key={item.key} value={item.key}>
                          {cyberCountry(item.key)}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}
              {(query || (tab === 'activity' && (country || actor || kind !== 'all'))) && (
                <Button variant="ghost" onClick={clear}>
                  Clear filters
                </Button>
              )}
            </div>
            {actor && tab === 'activity' && (
              <p className="text-xs text-cyan">
                Actor mentions: {selectedName ?? actor}{' '}
                <button type="button" className="ml-3 underline" onClick={() => setActor('')}>
                  Clear actor filter
                </button>
              </p>
            )}
            {data && (
              <p className="text-xs leading-5 text-muted">
                {tab === 'activity' ? items.length : vulnerabilities.length} matching records in the{' '}
                {data.returned_count} returned.{' '}
                {data.truncated
                  ? `The newest ${data.returned_count} of ${data.retained_count} records are listed. Overview counts include the wider retained selection.`
                  : 'Overview counts cover the complete retained selection for this period.'}
              </p>
            )}
          </section>
        )}
        {tab === 'activity' && data && (
          <CyberActivity
            key={`${days}:${query}:${kind}:${country}:${actor}:${snapshot.key}`}
            items={items}
            days={days}
            onActor={inspectActor}
          />
        )}
        {tab === 'vulnerabilities' && data && <CyberVulnerabilities items={vulnerabilities} />}
        {tab === 'actors' && (
          <>
            {actors.loading && <LoadingNote label="Loading threat actor references" />}
            {actors.error && (
              <Alert tone="error">
                {describeError(actors.error)}{' '}
                <Button variant="ghost" onClick={() => void actors.reload()}>
                  Retry actor references
                </Button>
              </Alert>
            )}
            {actors.data && (
              <CyberActors
                key={actors.key}
                data={actors.data}
                items={data?.items ?? []}
                mentions={data?.actor_mentions ?? []}
                activityStatus={data ? 'ready' : snapshot.loading ? 'loading' : 'unavailable'}
                selectedId={selectedActor}
                onSelect={setSelectedActor}
                onActivity={(id) => {
                  setActor(id);
                  setCountry('');
                  setKind('all');
                  setQuery('');
                  setTab('activity');
                }}
              />
            )}
          </>
        )}
        {tab === 'briefing' && <CyberBriefing state={briefing} days={days} />}
        {data && <CyberSourceCoverage data={data} />}
      </div>
    </section>
  );
}
