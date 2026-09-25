import { Sparkline } from '@/components/charts/Sparkline';
import { SourceLink } from '@/components/ui/SourceLink';
import type { CyberSnapshot, CyberTheme } from '@/lib/api/cyber';
import type { Report } from '@/lib/api/reports';
import { CYBER_KIND_LABELS } from '@/lib/cyber';
import { formatUtc } from '@/lib/format';
import { briefingPassage } from './cyberBriefingModel';
import { themeViews } from './cyberModel';

/** One card per lens: the count and trend, the briefing's own words, and the latest matches. */
export function CyberFocusAreas({
  data,
  report,
  onTheme,
}: {
  data: CyberSnapshot;
  report: Report | null;
  onTheme: (theme: CyberTheme) => void;
}) {
  return (
    <ul aria-label="Cyber focus areas" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {themeViews(data).map((view) => {
        const passage = report ? briefingPassage(report, view.theme) : null;
        return (
          <li
            key={view.theme}
            className="flex flex-col rounded-xl border border-line/70 bg-surface/60 p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold">{view.label}</h3>
                <p className="mt-1 text-[11px] leading-5 text-muted">{view.detail}</p>
              </div>
              <div className="w-28 shrink-0 text-right">
                <p className="text-2xl font-semibold tracking-tight">
                  {view.count.toLocaleString('en-GB')}
                </p>
                <Sparkline
                  values={view.daily}
                  slot={view.slot}
                  label={`${view.label} matches per day: ${view.daily.join(', ')}`}
                />
              </div>
            </div>
            <div className="mt-4 border-t border-line/60 pt-3">
              <p className="font-mono text-2xs tracking-[0.18em] text-cyan uppercase">
                {passage ? 'From the AI briefing' : 'AI briefing'}
              </p>
              {passage ? (
                <p className="mt-2 text-sm leading-6 text-text/90">{passage.text}</p>
              ) : (
                <p className="mt-2 text-xs leading-5 text-muted">
                  {report
                    ? 'The briefing has no passage under this heading for the period. Absence of a passage is not absence of activity.'
                    : 'A themed passage appears here once the cited briefing for this period is ready.'}
                </p>
              )}
            </div>
            <div className="mt-4 border-t border-line/60 pt-3">
              <p className="text-[11px] font-medium text-muted">Latest matched reporting</p>
              {view.items.length ? (
                <ul className="mt-2 space-y-2">
                  {view.items.map((item) => (
                    <li key={item.id} className="text-xs leading-5">
                      <SourceLink url={item.url}>{item.title}</SourceLink>
                      <p className="text-muted">
                        {CYBER_KIND_LABELS[item.kind]} · {item.source_name} ·{' '}
                        {formatUtc(item.published_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-xs leading-5 text-muted">
                  No returned record matches this lens in the period.
                </p>
              )}
            </div>
            <div className="mt-auto flex flex-wrap gap-3 pt-4 text-xs">
              <button
                type="button"
                onClick={() => onTheme(view.theme)}
                className="text-ember hover:underline"
              >
                Filter activity by this lens
              </button>
              {view.theme === 'gnss_interference' && (
                <a href="#cyber-gnss" className="text-ember hover:underline">
                  View the interference map summary
                </a>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
