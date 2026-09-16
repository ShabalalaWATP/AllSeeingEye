import type { Report } from '@/lib/api/reports';
import type { EconomyNewsItem } from '@/lib/api/economy';
import type { EconomyBriefing } from '@/lib/api/economyBriefing';
import { SourceLink } from '@/components/ui/SourceLink';
import { formatUtc } from '@/lib/format';
import type { RegionCode } from './economyPresentation';

const countryHeading: Record<Exclude<RegionCode, 'WORLD'>, RegExp> = {
  GB: /\b(united kingdom|uk|britain)\b/i,
  US: /\b(united states|usa)\b|\bu\.s\.(?=\W|$)/i,
  RU: /\brussia\b/i,
  CN: /\bchina\b/i,
  IR: /\biran\b/i,
};

/**
 * Reuse the cited briefing. While it is unavailable, show attributed headline extracts,
 * unless a checked plain-English summary already leads this part of the page.
 */
export function EconomyNewsOverview({
  items,
  region,
  report,
  briefing,
  explainerLeads = false,
}: {
  items: readonly EconomyNewsItem[];
  region: RegionCode;
  report: Report | null;
  briefing: EconomyBriefing | null;
  explainerLeads?: boolean;
}) {
  const judgement = region === 'WORLD' ? report?.version.body.key_judgements[0] : undefined;
  const assessment =
    region === 'WORLD'
      ? undefined
      : report?.version.body.assessment.find((item) => countryHeading[region].test(item.heading));
  // The opening authored paragraph is the takeaway; the full assessment stays below.
  const text = (judgement?.statement ?? assessment?.text)?.trim().split(/\r?\n\s*\r?\n/)[0];
  const labels = judgement
    ? [...judgement.supporting_evidence, ...judgement.contradicting_evidence]
    : (assessment?.evidence ?? []);
  const references = report?.version.evidence.filter((item) => labels.includes(item.label)) ?? [];
  const sourced = text && references.length > 0;
  if (!sourced && (explainerLeads || items.length === 0)) return null;
  return (
    <div className="border-l-2 border-ember pl-4 py-1">
      <p className="max-w-4xl text-[0.95rem] leading-7 text-text">
        {sourced ? (
          <>
            {text}
            {references.map((item, index) => (
              <span key={item.label} className="ml-1 text-xs">
                <SourceLink url={item.url}>
                  [{index + 1}] {item.source_name}
                </SourceLink>
              </span>
            ))}
          </>
        ) : (
          <>
            The leading available reports include{' '}
            {items.slice(0, 2).map((item, index) => (
              <span key={item.id}>
                {index > 0 ? ' and ' : ''}
                <SourceLink url={item.url}>{item.title}</SourceLink> ({item.source_name})
              </span>
            ))}
            . These are publisher reports; the cited assessment below provides the wider context
            when available.
          </>
        )}
      </p>
      {sourced && briefing && (
        <p className="mt-2 text-[11px] leading-5 text-muted">
          From the {briefing.window_days}-day briefing: {formatUtc(briefing.period_from)} to{' '}
          {formatUtc(briefing.period_to)}.
          {report?.version.status !== 'ready' ? ' This assessment needs review.' : ''}
        </p>
      )}
    </div>
  );
}
