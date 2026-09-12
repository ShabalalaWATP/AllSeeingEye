import type { CyberSnapshot } from '@/lib/api/cyber';
import { CYBER_KIND_LABELS } from '@/lib/cyber';
import { cyberCountry } from './cyberPresentation';

export function CyberOverview({
  data,
  onCountry,
  onActor,
}: {
  data: CyberSnapshot;
  onCountry: (country: string) => void;
  onActor: (actor: string) => void;
}) {
  const counts = Object.fromEntries(data.counts.map((item) => [item.kind, item.count]));
  const leadActor = data.actor_mentions[0];
  const max = Math.max(1, ...data.timeline.map((item) => item.total));
  const quantity = (count: number, noun: string) =>
    `${count.toLocaleString()} ${noun}${count === 1 ? '' : 's'}`;
  return (
    <section aria-label="Cyber activity overview" className="space-y-6">
      <div className="max-w-5xl border-l-2 border-cyan pl-4">
        <h2 className="text-lg font-semibold">The current picture</h2>
        <p className="mt-2 text-sm leading-7 text-text/90">
          {data.retained_count ? (
            <>
              The connected sources contain{' '}
              <strong>{quantity(data.retained_count, 'dated record')}</strong> in this period,
              including {quantity(counts.ransomware_claim ?? 0, 'ransomware claim')},{' '}
              {quantity(counts.known_exploited_vulnerability ?? 0, 'addition')} to CISA’s
              exploited-vulnerability catalogue and{' '}
              {quantity(counts.outage_signal ?? 0, 'connectivity signal')}.
              {leadActor && (
                <>
                  {' '}
                  {leadActor.name} is the most frequently matched actor name, appearing in{' '}
                  {quantity(leadActor.count, 'record')}. A name match is a research lead, not
                  confirmed attribution.
                </>
              )}
            </>
          ) : (
            <>
              No dated cyber records are currently available in this period. Check source coverage
              below; an empty feed does not indicate an absence of threats.
            </>
          )}
        </p>
      </div>
      <div className="grid gap-8 border-y border-line py-6 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold">Reporting activity</h3>
            <span className="font-mono text-[10px] text-muted">UTC · records per calendar day</span>
          </div>
          <svg
            viewBox="0 0 620 140"
            role="img"
            aria-label="Daily cyber reporting volume"
            className="mt-4 w-full overflow-visible"
          >
            <line x1="0" y1="112" x2="620" y2="112" stroke="currentColor" className="text-line" />
            {data.timeline.map((day, index) => {
              const slot = 620 / Math.max(1, data.timeline.length);
              const height = (day.total / max) * 94;
              return (
                <g key={day.day}>
                  <title>
                    {day.day}: {day.total} records
                  </title>
                  <rect
                    x={index * slot + slot * 0.14}
                    y={112 - height}
                    width={slot * 0.72}
                    height={height}
                    rx="2"
                    fill="currentColor"
                    className="text-cyan/75"
                  />
                  <text
                    x={index * slot + slot / 2}
                    y="133"
                    textAnchor="middle"
                    fontSize="9"
                    fill="currentColor"
                    className="text-muted"
                  >
                    {day.day.slice(5)}
                  </text>
                </g>
              );
            })}
          </svg>
          <p className="mt-2 text-xs leading-5 text-muted">
            Report volume measures source output, not attack severity. The first and last days can
            be partial; outages may have multiple sensor records.
          </p>
          <details className="mt-3 text-xs text-muted">
            <summary className="w-fit cursor-pointer hover:text-text">
              Daily counts by evidence type
            </summary>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left">
                <caption className="sr-only">Dated cyber records, split by type</caption>
                <thead>
                  <tr>
                    <th className="py-2 pr-4">Date (UTC)</th>
                    {data.counts.map((count) => (
                      <th className="px-2" key={count.kind}>
                        {CYBER_KIND_LABELS[count.kind]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.timeline.map((day) => (
                    <tr className="border-t border-line" key={day.day}>
                      <th className="whitespace-nowrap py-2 pr-4 font-normal">{day.day}</th>
                      {data.counts.map((count) => (
                        <td className="px-2 font-mono" key={count.kind}>
                          {day.counts.find((item) => item.kind === count.kind)?.count ?? 0}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-1">
          <div>
            <h3 className="text-sm font-semibold">Actor names in reporting</h3>
            <p className="mt-1 text-xs text-muted">
              Matched mentions, not a ranking of threat capability.
            </p>
            <ul className="mt-3 space-y-1">
              {data.actor_mentions.slice(0, 5).map((actor) => (
                <li key={actor.group_id}>
                  <button
                    type="button"
                    onClick={() => onActor(actor.group_id)}
                    className="flex min-h-9 w-full items-center justify-between gap-3 rounded px-2 text-left text-sm hover:bg-surface-2"
                  >
                    <span>{actor.name}</span>
                    <span className="font-mono text-xs text-cyan">{actor.count}</span>
                  </button>
                </li>
              ))}
            </ul>
            {!data.actor_mentions.length && (
              <p className="mt-3 text-xs text-muted">
                No distinctive actor names matched the available reporting.
              </p>
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold">Countries in the evidence</h3>
            <p className="mt-1 text-xs text-muted">
              Source-supplied context, not attacker origins.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.top_countries.slice(0, 6).map((item) => (
                <button
                  type="button"
                  key={item.key}
                  onClick={() => onCountry(item.key)}
                  className="rounded-md bg-surface px-3 py-2 text-xs hover:bg-surface-2"
                >
                  {cyberCountry(item.key)}{' '}
                  <span className="ml-2 font-mono text-muted">{item.count}</span>
                </button>
              ))}
            </div>
            {!data.top_countries.length && (
              <p className="mt-3 text-xs text-muted">
                Locations are not established for these records.
              </p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
