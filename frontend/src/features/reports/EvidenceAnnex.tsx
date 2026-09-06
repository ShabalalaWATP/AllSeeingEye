import type { ReactNode } from 'react';

import type { EvidenceItem, Finding } from '@/lib/api/reports';
import { formatUtc } from '@/lib/format';
import { isHttpUrl } from '@/lib/urls';

import { evidenceId } from './EvidenceLinks';

function Metadata({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-1 text-sm [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

function known(value: string | null | undefined): string {
  return value?.trim() ? value : 'Unknown';
}

function time(value: string | null | undefined): string {
  return value && Number.isFinite(Date.parse(value)) ? formatUtc(value) : 'Unknown';
}

function SourceLink({ url, children }: { url: string | null; children: ReactNode }) {
  if (!isHttpUrl(url)) return null;
  const parsed = new URL(url);
  if (
    parsed.username ||
    parsed.password ||
    Array.from(url).some(
      (character) => character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127,
    )
  )
    return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-ember underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember"
    >
      {children}
    </a>
  );
}

function EvidenceDetails({ item }: { item: EvidenceItem }) {
  return (
    <details id={evidenceId(item.label)} className="group scroll-mt-6 border-b border-line py-1">
      <summary className="cursor-pointer rounded py-3 text-sm transition-colors hover:bg-surface-2/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember motion-reduce:transition-none">
        <span className="ml-2 inline-grid w-[calc(100%-2rem)] grid-cols-[2.5rem_minmax(0,1fr)_auto] gap-3 align-top">
          <span className="font-mono text-xs text-ember">{item.label}</span>
          <span className="min-w-0">
            <span className="block font-medium [overflow-wrap:anywhere]">{item.title}</span>
            <span className="mt-1 block text-xs text-muted [overflow-wrap:anywhere]">
              {item.source_name} · {time(item.published_at)}
            </span>
          </span>
          <span className="font-mono text-xs text-muted">{item.grade}</span>
        </span>
      </summary>
      <div className="flex min-w-0 flex-col gap-4 pb-5 pl-5 sm:pl-12">
        {item.title_en && (
          <div>
            <h3 className="text-xs font-medium text-muted">Translation (unverified)</h3>
            <p className="mt-1 text-sm [overflow-wrap:anywhere]">{item.title_en}</p>
          </div>
        )}
        {item.summary && (
          <div>
            <h3 className="text-xs font-medium text-muted">Original source snippet</h3>
            <p className="mt-1 text-sm [overflow-wrap:anywhere]">{item.summary}</p>
          </div>
        )}
        <dl className="grid min-w-0 gap-x-8 gap-y-4 sm:grid-cols-2">
          <Metadata label="Grade rationale">{item.grade_rationale || 'Not provided'}</Metadata>
          <Metadata label="Reliability / credibility">
            {item.reliability ?? 'Unknown'} / {item.credibility ?? 'Unknown'}
          </Metadata>
          <Metadata label="Published">{time(item.published_at)}</Metadata>
          <Metadata label="Observed">{time(item.observed_at)}</Metadata>
          <Metadata label="Captured">{time(item.captured_at)}</Metadata>
          <Metadata label="Language">{known(item.language)}</Metadata>
          <Metadata label="Location precision">{known(item.geo_confidence)}</Metadata>
          <Metadata label="Country">{known(item.country_iso)}</Metadata>
          <Metadata label="Coordinates (longitude, latitude)">
            {item.lon == null || item.lat == null
              ? 'Unknown'
              : `${String(item.lon)}, ${String(item.lat)}`}
          </Metadata>
          <Metadata label="Declared organisation">{known(item.independence_key)}</Metadata>
          <Metadata label="Source ID">{item.source_id}</Metadata>
          <Metadata label="Topic cluster">{known(item.story_id)}</Metadata>
          <Metadata label="Event ID">
            <span className="font-mono text-xs">{item.event_id}</span>
          </Metadata>
          <Metadata label="Content hash">
            <span className="font-mono text-xs">{known(item.content_hash)}</span>
          </Metadata>
        </dl>
        <p className="text-xs text-muted">
          Independent sourcing is not verified; topic grouping does not establish corroboration.
          Coordinates reflect the recorded location precision.
        </p>
        {item.flags.length > 0 && (
          <p className="text-xs text-amber [overflow-wrap:anywhere]">
            Source flags: {item.flags.join(', ').replace(/_/g, ' ')}
          </p>
        )}
        <div className="flex flex-wrap gap-4 text-xs">
          <SourceLink url={item.url}>Open source</SourceLink>
          <SourceLink url={item.archive_url}>Open archive</SourceLink>
        </div>
      </div>
    </details>
  );
}

export function EvidenceAnnex({
  evidence,
  findings,
  status,
}: {
  evidence: readonly EvidenceItem[];
  findings: readonly Finding[];
  status: string;
}) {
  const warnings = findings.filter((finding) => finding.severity === 'warning');
  return (
    <div className="flex min-w-0 flex-col gap-4 text-sm">
      {status === 'ready' && warnings.length > 0 && (
        <details className="text-xs text-muted">
          <summary className="cursor-pointer">{warnings.length} validator note(s)</summary>
          <ul className="mt-2 list-disc pl-5">
            {warnings.map((finding, index) => (
              <li key={index}>
                {finding.location}: {finding.message}
              </li>
            ))}
          </ul>
        </details>
      )}
      <section aria-label="Evidence annex" className="min-w-0">
        <h2 className="text-base font-semibold">Evidence annex</h2>
        <p className="mt-1 mb-3 text-xs text-muted">
          Open a source to inspect its frozen metadata and snippet. Full source content and
          translations are not independently verified.
        </p>
        {evidence.length === 0 ? (
          <p className="text-sm text-muted">No frozen evidence was saved for this version.</p>
        ) : (
          evidence.map((item) => <EvidenceDetails key={item.label} item={item} />)
        )}
      </section>
    </div>
  );
}
