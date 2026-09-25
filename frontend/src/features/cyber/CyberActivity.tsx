import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { SourceLink } from '@/components/ui/SourceLink';
import { Button } from '@/components/ui/Button';
import type { CyberDays, CyberItem, CyberTheme } from '@/lib/api/cyber';
import { CYBER_KIND_LABELS } from '@/lib/cyber';
import { CYBER_THEME_META } from '@/lib/cyberThemes';
import { formatUtc } from '@/lib/format';
import { prepareCyberMap } from '@/stores/cyberFilters';
import { KIND_NOTES, cyberCountry, cyberResearchLink } from './cyberPresentation';

export function CyberActivity({
  items,
  days,
  onActor,
  onTheme,
}: {
  items: readonly CyberItem[];
  days: CyberDays;
  onActor: (id: string) => void;
  onTheme?: ((theme: CyberTheme) => void) | undefined;
}) {
  const navigate = useNavigate();
  const [limit, setLimit] = useState(30);
  if (!items.length)
    return (
      <p className="rounded-xl border border-dashed border-line/70 px-4 py-10 text-center text-sm text-muted">
        No records match these filters in the returned reporting. Try a broader period or clear a
        filter.
      </p>
    );
  return (
    <div className="space-y-5">
      <ol aria-label="Cyber activity reports" className="space-y-3">
        {items.slice(0, limit).map((item) => (
          <li
            key={item.id}
            className="grid gap-4 rounded-xl border border-line/60 bg-surface/50 p-4 transition-colors hover:border-line lg:grid-cols-[11rem_1fr] lg:gap-7 lg:p-5"
          >
            <div className="space-y-1.5 text-[11px] leading-5 text-muted">
              <p className="font-medium text-cyan">{CYBER_KIND_LABELS[item.kind]}</p>
              <time dateTime={item.published_at} className="block">
                {formatUtc(item.published_at)}
              </time>
              <p>{cyberCountry(item.country_iso)}</p>
              <p className="font-mono text-2xs">Grade {item.grade}</p>
            </div>
            <div className="min-w-0 space-y-3">
              <h3 className="text-base leading-7 font-semibold">
                <SourceLink url={item.url}>{item.title}</SourceLink>
              </h3>
              <p className="text-xs text-muted">{item.source_name}</p>
              {item.summary && (
                <p className="max-w-4xl text-sm leading-7 whitespace-pre-line text-text/90">
                  {item.summary}
                </p>
              )}
              <p className="max-w-4xl text-xs leading-5 text-muted">{KIND_NOTES[item.kind]}</p>
              {(item.actor_mentions.length > 0 || item.themes.length > 0) && (
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {item.themes.map((theme) => (
                    <button
                      key={theme}
                      type="button"
                      onClick={() => onTheme?.(theme)}
                      title={CYBER_THEME_META[theme].label}
                      className="rounded-full border border-line/70 px-2.5 py-0.5 text-[11px] text-muted hover:border-cyan hover:text-text"
                    >
                      {CYBER_THEME_META[theme].short}
                    </button>
                  ))}
                  {item.actor_mentions.length > 0 && (
                    <span className="ml-1 text-muted">Names mentioned:</span>
                  )}
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
