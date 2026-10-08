import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { LAUNCHER_SCROLL_PADDING } from '@/components/assistant/launcherClearance';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { SectionPendingNote } from '@/components/ui/SectionPending';
import { parseCyberDays, type CyberDays, type CyberTheme } from '@/lib/api/cyber';
import { describeError } from '@/lib/api/errors';
import { CYBER_KIND_LABELS, type CyberKindFilter } from '@/lib/cyber';
import { CYBER_THEME_META } from '@/lib/cyberThemes';
import { prepareCyberMap } from '@/stores/cyberFilters';
import { useGlobeStore } from '@/stores/globe';
import { CyberActivity } from './CyberActivity';
import { CyberActors } from './CyberActors';
import { CyberAssessment } from './CyberAssessment';
import { CyberBriefing } from './CyberBriefing';
import { CyberCharts } from './CyberCharts';
import { CYBER_FIELD, CyberFilterSelect } from './CyberFilterSelect';
import { CyberFocusAreas } from './CyberFocusAreas';
import { CyberGnss } from './CyberGnss';
import { CyberHeader } from './CyberHeader';
import { CyberKpis } from './CyberKpis';
import { CyberNationState } from './CyberNationState';
import { CyberLiveBoard } from './CyberLiveBoard';
import { CyberSectionNav, Section } from './CyberSectionNav';
import { CyberSourceCoverage } from './CyberSourceCoverage';
import { CyberVulnerabilities } from './CyberVulnerabilities';
import { cyberCountry, filterCyberItems } from './cyberPresentation';
import { useCyberWorkspace } from './useCyberWorkspace';

const THEME_OPTIONS = Object.entries(CYBER_THEME_META).map(
  ([key, meta]) => [key as CyberTheme, meta.label] as const,
);

export default function CyberPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const days = parseCyberDays(params.get('days'));
  const [query, setQuery] = useState('');
  const [country, setCountry] = useState('');
  const [kind, setKind] = useState<CyberKindFilter>('all');
  const [actor, setActor] = useState('');
  const [theme, setTheme] = useState<CyberTheme | ''>('');
  const [selectedActor, setSelectedActor] = useState('');
  const { snapshot, actors, briefing, gnss, live } = useCyberWorkspace(days);
  const data = snapshot.data;
  const items = useMemo(
    () => filterCyberItems(data?.items ?? [], query, kind, country, actor, theme),
    [data, query, kind, country, actor, theme],
  );
  const vulnerabilities = useMemo(
    () => filterCyberItems(data?.items ?? [], query, 'known_exploited_vulnerability', '', ''),
    [data, query],
  );
  const gnssItems = useMemo(
    () => (data?.items ?? []).filter((item) => item.themes.includes('gnss_interference')),
    [data],
  );
  const catalogue = actors.data?.catalogue?.actors ?? [];
  const selectedName = catalogue.find((item) => item.group_id === actor)?.name;
  const actorStatus = data ? 'ready' : snapshot.loading ? 'loading' : 'unavailable';
  const pending =
    briefing.briefing?.job.status === 'running' || briefing.briefing?.job.status === 'queued';
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ block: 'start' });
  const inspectActor = (id: string) => {
    setSelectedActor(id);
    jump('cyber-actors');
  };
  const focusActivity = (changes: Partial<{ country: string; theme: CyberTheme | '' }>) => {
    if (changes.country !== undefined) setCountry(changes.country);
    if (changes.theme !== undefined) setTheme(changes.theme);
    jump('cyber-activity');
  };
  const clear = () => {
    setQuery('');
    setCountry('');
    setKind('all');
    setActor('');
    setTheme('');
  };
  const setDays = (value: CyberDays) =>
    setParams((previous) => {
      previous.set('days', String(value));
      return previous;
    });
  const openGnssMap = () => {
    const globe = useGlobeStore.getState();
    if (!globe.interference) globe.toggleInterference();
    void navigate('/');
  };
  const filtered = Boolean(query || country || actor || theme || kind !== 'all');
  const snapshotPending = (
    <SectionPendingNote loading={snapshot.loading} subject="cyber activity" />
  );
  return (
    // Focus scrolling leaves room for the sticky section bar above and the Eye launcher below.
    <section
      className={`h-full min-w-0 scroll-pt-16 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10 ${LAUNCHER_SCROLL_PADDING}`}
    >
      <div className="mx-auto max-w-[1500px] space-y-8 pb-28">
        <CyberHeader
          days={days}
          onDays={setDays}
          data={data}
          loading={snapshot.loading}
          onRefresh={() => void snapshot.reload()}
          onOpenMap={() =>
            void navigate(prepareCyberMap({ country: country || null, days, kind, query }))
          }
        />
        <CyberSectionNav preparing={pending} />
        {snapshot.loading && !data && <LoadingNote label="Loading cyber activity" />}
        {snapshot.error && (
          <Alert tone="error">
            {describeError(snapshot.error)}{' '}
            <Button variant="ghost" onClick={() => void snapshot.reload()}>
              Retry cyber sources
            </Button>
          </Alert>
        )}
        <Section
          id="cyber-overview"
          eyebrow="Overview"
          title="The current picture"
          lede="Collected records for the selected period, split by what each source actually measures."
        >
          {data ? (
            <>
              <CyberKpis data={data} />
              <CyberCharts data={data} onCountry={(value) => focusActivity({ country: value })} />
            </>
          ) : (
            snapshotPending
          )}
        </Section>
        <Section
          id="cyber-live"
          eyebrow="Live board"
          title="Outages and ransomware claims now"
          lede="Counted from the live event feed, whatever period is chosen above: internet outage alerts from the last 24 hours and ransomware claims from the last 7 days. Claims are criminal statements, graded possibly true."
        >
          <CyberLiveBoard state={live} />
        </Section>
        <Section
          id="cyber-assessment"
          eyebrow="Assessment"
          title="AI assessment of the period"
          lede="A source-backed executive view written by the configured model from the collected evidence. Filters on this page never change its scope."
        >
          <CyberAssessment state={briefing} days={days} />
        </Section>
        <Section
          id="cyber-focus"
          eyebrow="Focus areas"
          title="Themed lenses on the reporting"
          lede="Nation-state tradecraft, the alliance, UK infrastructure, Ukraine, navigation interference and operational technology, each with the briefing’s own words when it has them."
        >
          {data ? (
            <CyberFocusAreas
              data={data}
              report={briefing.report}
              onTheme={(value) => focusActivity({ theme: value })}
            />
          ) : (
            snapshotPending
          )}
        </Section>
        <Section
          id="cyber-nation-state"
          eyebrow="Nation-state"
          title="State-associated actor mentions"
          lede="Where reporting names a group whose MITRE ATT&CK profile records a state association. Mentions are leads for research, not attribution."
        >
          {data ? (
            <CyberNationState
              data={data}
              actors={catalogue}
              actorStatus={actors.data ? 'ready' : actors.loading ? 'loading' : 'unavailable'}
              onActor={inspectActor}
            />
          ) : (
            snapshotPending
          )}
        </Section>
        <Section
          id="cyber-gnss"
          eyebrow="GNSS"
          title="GPS and GNSS interference"
          lede="Aircraft accuracy anomalies from the aviation tracker, read by region, beside reporting that mentions jamming or spoofing."
        >
          {data ? (
            <CyberGnss gnss={gnss} items={gnssItems} onOpenMap={openGnssMap} />
          ) : (
            snapshotPending
          )}
        </Section>
        <Section
          id="cyber-vulnerabilities"
          eyebrow="Exploitation"
          title="Exploited vulnerabilities to prioritise"
          lede="Recent additions to CISA’s Known Exploited Vulnerabilities catalogue. Match affected products to your own estate before acting; catalogue addition is not the date exploitation began."
        >
          {data ? <CyberVulnerabilities items={vulnerabilities} /> : snapshotPending}
        </Section>
        <Section
          id="cyber-actors"
          eyebrow="Reference"
          title="Threat actor reference"
          lede="Historical MITRE ATT&CK profiles with this period’s name matches."
        >
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
              activityStatus={actorStatus}
              selectedId={selectedActor}
              onSelect={setSelectedActor}
              onActivity={(id) => {
                setActor(id);
                setCountry('');
                setKind('all');
                setQuery('');
                setTheme('');
                jump('cyber-activity');
              }}
            />
          )}
        </Section>
        <Section
          id="cyber-activity"
          eyebrow="Activity"
          title="Collected reporting"
          lede="Every returned record with its source, grade, lenses and matched names."
        >
          <div aria-label="Filter cyber reporting" className="space-y-3">
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex min-w-48 flex-1 flex-col gap-2 text-xs text-muted">
                Search returned reports
                <input
                  type="search"
                  value={query}
                  maxLength={120}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Actor, CVE, product or keyword"
                  className={CYBER_FIELD}
                />
              </label>
              <label className="flex flex-col gap-2 text-xs text-muted">
                Evidence type
                <select
                  value={kind}
                  onChange={(event) => setKind(event.target.value as CyberKindFilter)}
                  className={CYBER_FIELD}
                >
                  <option value="all">All cyber reporting</option>
                  {Object.entries(CYBER_KIND_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <CyberFilterSelect
                label="Country context"
                value={country}
                onChange={setCountry}
                allLabel="All locations"
                options={(data?.top_countries ?? []).map((item) => [
                  item.key,
                  cyberCountry(item.key),
                ])}
              />
              <CyberFilterSelect<CyberTheme>
                label="Lens"
                value={theme}
                onChange={setTheme}
                allLabel="All lenses"
                options={THEME_OPTIONS}
              />
              {filtered && (
                <Button variant="ghost" onClick={clear}>
                  Clear filters
                </Button>
              )}
            </div>
            {actor && (
              <p className="text-xs text-cyan">
                Actor mentions: {selectedName ?? actor}{' '}
                <button type="button" className="ml-3 underline" onClick={() => setActor('')}>
                  Clear actor filter
                </button>
              </p>
            )}
            {data && (
              <p className="text-xs leading-5 text-muted">
                {items.length} matching records in the {data.returned_count} returned.{' '}
                {data.truncated
                  ? `The newest ${data.returned_count} of ${data.retained_count} records are listed. Overview counts include the wider retained selection.`
                  : 'Overview counts cover the complete retained selection for this period.'}
              </p>
            )}
          </div>
          {data ? (
            <CyberActivity
              key={`${days}:${query}:${kind}:${country}:${actor}:${theme}:${snapshot.key}`}
              items={items}
              days={days}
              onActor={inspectActor}
              onTheme={(value) => focusActivity({ theme: value })}
            />
          ) : (
            snapshotPending
          )}
        </Section>
        <Section
          id="cyber-briefing"
          eyebrow="Briefing"
          title="Full cited briefing"
          lede="The complete assessment with judgements, developments, watch conditions and references."
        >
          <CyberBriefing state={briefing} days={days} />
        </Section>
        <Section
          id="cyber-sources"
          eyebrow="Sources"
          title="Coverage and limitations"
          lede="Which feeds contributed, their delivery health and what the counts can and cannot say."
        >
          {data ? <CyberSourceCoverage data={data} /> : snapshotPending}
        </Section>
      </div>
    </section>
  );
}
