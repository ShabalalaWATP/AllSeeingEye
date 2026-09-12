import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { SourceLink } from '@/components/ui/SourceLink';
import { Button } from '@/components/ui/Button';
import type { CyberDays, CyberItem } from '@/lib/api/cyber';
import { CYBER_KIND_LABELS } from '@/lib/cyber';
import { formatUtc } from '@/lib/format';
import { prepareCyberMap } from '@/stores/cyberFilters';
import { KIND_NOTES, cyberCountry, cyberResearchLink } from './cyberPresentation';

export function CyberActivity({
  items,
  days,
  onActor,
}: {
  items: readonly CyberItem[];
  days: CyberDays;
  onActor: (id: string) => void;
}) {
  const navigate = useNavigate();
  const [limit, setLimit] = useState(30);
  if (!items.length)
    return (
      <p className="border-y border-line py-10 text-sm text-muted">
        No records match these filters in the returned reporting. Try a broader period or clear a
        filter.
      </p>
    );
  return (
    <div className="space-y-5">
      <ol aria-label="Cyber activity reports" className="divide-y divide-line">
        {items.slice(0, limit).map((item) => (
          <li
            key={item.id}
            className="grid gap-4 py-6 first:pt-0 lg:grid-cols-[10rem_1fr] lg:gap-7"
          >
            <div className="space-y-2 text-[11px] leading-5 text-muted">
              <p className="font-medium text-cyan">{CYBER_KIND_LABELS[item.kind]}</p>
              <time dateTime={item.published_at}>{formatUtc(item.published_at)}</time>
              <p>{cyberCountry(item.country_iso)}</p>
            </div>
            <div className="min-w-0 space-y-3">
              <h3 className="text-base font-semibold leading-7">
                <SourceLink url={item.url}>{item.title}</SourceLink>
              </h3>
              <p className="text-xs text-muted">
                {item.source_name} · Source grade {item.grade}
              </p>
              {item.summary && (
                <p className="max-w-4xl whitespace-pre-line text-sm leading-7 text-text/90">
                  {item.summary}
                </p>
              )}
              <p className="max-w-4xl text-xs leading-5 text-muted">{KIND_NOTES[item.kind]}</p>
              {item.actor_mentions.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-muted">Names mentioned:</span>
                  {item.actor_mentions.map((actor) => (
                    <button
                      key={actor.group_id}
                      type="button"
                      onClick={() => onActor(actor.group_id)}
                      className="rounded bg-surface px-2 py-1 text-cyan hover:bg-surface-2"
                    >
                      {actor.matched_name}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap items-center gap-4">
                <Link
                  className="text-xs text-ember hover:underline"
                  to={cyberResearchLink(item.title)}
                >
                  Research this report
                </Link>
                {item.country_iso && (
                  <Button
                    variant="ghost"
                    className="text-xs"
                    onClick={() =>
                      void navigate(
                        prepareCyberMap({ country: item.country_iso, days, kind: item.kind }),
                      )
                    }
                  >
                    View country context on map
                  </Button>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
      {items.length > limit && (
        <Button variant="secondary" onClick={() => setLimit((value) => value + 30)}>
          Show more reports ({items.length - limit} remaining)
        </Button>
      )}
    </div>
  );
}
