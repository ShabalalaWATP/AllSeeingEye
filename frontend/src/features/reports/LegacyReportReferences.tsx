import { SourceLink } from '@/components/ui/SourceLink';
import type { EvidenceItem } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';

import { evidenceId } from './EvidenceLinks';

function sourceDate(value: string | null): string {
  return value && Number.isFinite(Date.parse(value)) ? formatUtc(value) : 'Date not reported';
}

/** A deterministic reader-local target for citations on pre-publication report responses. */
export function LegacyReportReferences({ evidence }: { evidence: readonly EvidenceItem[] }) {
  if (!evidence.length) return null;
  return (
    <section aria-label="References" className="report-reader-section">
      <h2>References</h2>
      <div className="mt-4">
        {evidence.map((item) => (
          <details
            key={item.label}
            id={evidenceId(item.label)}
            className="report-reader-legacy-reference scroll-mt-6"
          >
            <summary className="cursor-pointer rounded py-1 font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember">
              <span className="mr-2 font-mono text-xs text-[#9b3b18]">[{item.label}]</span>
              {item.source_name}. {item.title}. {sourceDate(item.published_at)}.
            </summary>
            <div className="mt-2 pl-8 text-xs leading-5 text-[#6d675e]">
              {item.summary && <p dir="auto">{item.summary}</p>}
              <p className="mt-2 flex flex-wrap gap-4">
                <SourceLink url={item.url}>Original source</SourceLink>
                <SourceLink url={item.archive_url}>Archived copy</SourceLink>
              </p>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
