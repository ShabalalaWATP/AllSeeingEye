import { useState } from 'react';
import { Link } from 'react-router';
import { SourceLink } from '@/components/ui/SourceLink';
import { Button } from '@/components/ui/Button';
import type { CyberActors as ActorResponse, CyberItem, CyberSnapshot } from '@/lib/api/cyber';
import { formatUtc } from '@/lib/format';
import { cyberResearchLink } from './cyberPresentation';

export function CyberActors({
  data,
  items,
  mentions,
  activityStatus,
  selectedId,
  onSelect,
  onActivity,
}: {
  data: ActorResponse;
  items: readonly CyberItem[];
  mentions: CyberSnapshot['actor_mentions'];
  activityStatus: 'ready' | 'loading' | 'unavailable';
  selectedId: string;
  onSelect: (id: string) => void;
  onActivity: (id: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(24);
  const catalogue = data.catalogue;
  if (!data.available || !catalogue)
    return <p className="border-l-2 border-amber pl-4 text-sm leading-6">{data.coverage_note}</p>;
  const filtered = catalogue.actors.filter((actor) =>
    [actor.name, actor.group_id, ...actor.associated_names, actor.description]
      .join(' ')
      .toLocaleLowerCase()
      .includes(query.toLocaleLowerCase().trim()),
  );
  const selected = catalogue.actors.find((actor) => actor.group_id === selectedId);
  const activityNote = activityStatus === 'loading' ? 'Activity loading' : 'Activity unavailable';
  const linked =
    selected && activityStatus === 'ready'
      ? items.filter((item) =>
          item.actor_mentions.some((mention) => mention.group_id === selected.group_id),
        )
      : [];
  const count =
    selected && activityStatus === 'ready'
      ? (mentions.find((mention) => mention.group_id === selected.group_id)?.count ?? 0)
      : null;
  return (
    <section aria-label="Threat actor reference" className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold">Threat actor reference</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">
          Explore {catalogue.actors.length} publicly documented groups and the activity currently
          mentioning them. Historical profiles describe reported tradecraft, not proof of
          responsibility for a new incident.
        </p>
      </header>
      <div className="grid items-start gap-7 xl:grid-cols-[1fr_1.2fr]">
        <div>
          <label className="block text-xs font-medium text-muted" htmlFor="cyber-actor-search">
            Search name, associated name, ID or profile
          </label>
          <input
            id="cyber-actor-search"
            type="search"
            maxLength={120}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setLimit(24);
            }}
            placeholder="APT29, Midnight Blizzard, Lazarus…"
            className="mt-2 min-h-11 w-full rounded-md border border-line bg-surface px-3 text-sm focus:border-ember focus:outline-none"
          />
          <p className="mt-3 text-xs text-muted">
            {filtered.length} matching profiles · MITRE ATT&CK {catalogue.version}
          </p>
          <ul className="mt-3 divide-y divide-line">
            {filtered.slice(0, limit).map((actor) => {
              const activity =
                mentions.find((mention) => mention.group_id === actor.group_id)?.count ?? 0;
              return (
                <li key={actor.group_id}>
                  <button
                    type="button"
                    aria-label={`View ${actor.name} (${actor.group_id}), ${activityStatus === 'ready' ? `${activity} mentions` : activityNote}`}
                    aria-pressed={selectedId === actor.group_id}
                    onClick={() => onSelect(actor.group_id)}
                    className={`flex min-h-16 w-full items-start justify-between gap-3 rounded px-3 py-3 text-left transition-colors ${selectedId === actor.group_id ? 'bg-surface-2' : 'hover:bg-surface'}`}
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold">{actor.name}</span>
                      <span className="mt-1 block truncate text-xs text-muted">
                        {actor.group_id} ·{' '}
                        {actor.associated_names.slice(0, 3).join(', ') ||
                          'No associated names listed'}
                      </span>
                    </span>
                    <span className="shrink-0 text-right font-mono text-xs text-cyan">
                      {activityStatus === 'ready' ? activity : '…'}
                      <span className="mt-1 block font-sans text-[10px] text-muted">
                        {activityStatus === 'ready' ? 'mentions' : activityNote}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {!filtered.length && (
            <p className="py-6 text-sm text-muted">No reference profiles match that search.</p>
          )}
          {filtered.length > limit && (
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => setLimit((value) => value + 24)}
            >
              Show more actors
            </Button>
          )}
        </div>
        <aside
          aria-label="Selected threat actor"
          className="border-l-2 border-cyan/60 pl-5 xl:sticky xl:top-6"
        >
          {selected ? (
            <div className="space-y-5">
              <header>
                <p className="font-mono text-[10px] text-cyan">
                  {selected.group_id} · HISTORICAL REFERENCE
                </p>
                <h3 className="mt-2 text-2xl font-semibold">{selected.name}</h3>
                <p className="mt-2 text-xs text-muted">
                  Profile modified {formatUtc(selected.modified_at)}
                </p>
              </header>
              <p className="whitespace-pre-line text-sm leading-7 text-text/90">
                {selected.description}
              </p>
              <p>
                <SourceLink url={selected.url}>
                  Read profile and original references on MITRE ATT&CK
                </SourceLink>
              </p>
              {selected.associated_names.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold">Associated group names</h4>
                  <p className="mt-2 text-sm leading-6">{selected.associated_names.join(' · ')}</p>
                  <p className="mt-2 text-xs leading-5 text-muted">
                    Names used by different researchers may overlap only partly. This is not a
                    verified identity crosswalk.
                  </p>
                </div>
              )}
              <div className="border-t border-line pt-4">
                <h4 className="text-sm font-semibold">Mentioned in this period</h4>
                <p className="mt-2 text-sm leading-6">
                  {count === null
                    ? `${activityNote}. Mention counts will appear when reporting for this period is available.`
                    : `Matched records: ${count}. ${count ? 'Read the source before accepting its attribution.' : 'No matching name was found in retained reporting; this does not establish inactivity.'}`}
                </p>
                <ul className="mt-3 space-y-3">
                  {linked.slice(0, 4).map((item) => (
                    <li key={item.id} className="text-xs leading-6">
                      <SourceLink url={item.url}>{item.title}</SourceLink>
                      <p className="text-muted">
                        {item.source_name} · {formatUtc(item.published_at)}
                      </p>
                    </li>
                  ))}
                </ul>
                {count !== null && count > 0 && (
                  <Button
                    variant="ghost"
                    className="mt-2"
                    onClick={() => onActivity(selected.group_id)}
                  >
                    Filter activity by this actor
                  </Button>
                )}
              </div>
              <details className="border-t border-line pt-4">
                <summary className="cursor-pointer text-sm font-medium">
                  Reported ATT&CK techniques ({selected.technique_count})
                </summary>
                <p className="mt-2 text-xs leading-5 text-muted">
                  Historical technique associations, not techniques confirmed in every new report.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selected.technique_ids.map((id) => (
                    <SourceLink
                      key={id}
                      url={`https://attack.mitre.org/techniques/${id.replace('.', '/')}/`}
                    >
                      {id}
                    </SourceLink>
                  ))}
                </div>
              </details>
              <Link
                className="inline-block rounded-md bg-ember px-4 py-2 text-sm font-medium text-ground"
                to={cyberResearchLink(selected.name)}
              >
                Research {selected.name}
              </Link>
            </div>
          ) : (
            <div className="py-8">
              <h3 className="text-lg font-semibold">Select a threat actor</h3>
              <p className="mt-3 max-w-lg text-sm leading-7 text-muted">
                See the attributed profile, associated names, reported techniques and matching
                activity in the selected period.
              </p>
            </div>
          )}
        </aside>
      </div>
      <details className="border-t border-line pt-4 text-xs leading-6 text-muted">
        <summary className="w-fit cursor-pointer">Reference provenance and limitations</summary>
        <p className="mt-3">{catalogue.attribution}</p>
        <p>{catalogue.limitations}</p>
        <p>
          Reference release {formatUtc(catalogue.released_at)}; retrieved{' '}
          {formatUtc(catalogue.retrieved_at)}.
        </p>
        <div className="flex flex-wrap gap-4">
          <SourceLink url={catalogue.source_url}>Source dataset</SourceLink>
          <SourceLink url={catalogue.licence_url}>Terms of use</SourceLink>
        </div>
      </details>
    </section>
  );
}
