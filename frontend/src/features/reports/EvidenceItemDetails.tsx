import type { ReactNode } from 'react';

import { EvidenceObservationDetails } from '@/components/maps/EvidenceObservationDetails';
import { EvidenceProjectDetails } from '@/components/maps/EvidenceProjectDetails';
import { SourceProvenanceDetails } from '@/components/reports/SourceProvenanceDetails';
import { SourceRatingDetails } from '@/components/sources/SourceRatingDetails';
import { SourceLink } from '@/components/ui/SourceLink';
import type { EvidenceItem } from '@/lib/api/reports';
import type { EvidenceAssessment } from '@/lib/api/reportAssessment';
import { formatUtc } from '@/lib/format';

import {
  credibilityTone,
  flagLabel,
  flagTone,
  gradeTone,
  reliabilityTone,
  type Tone,
} from './doctrineTone';
import { evidenceId } from './EvidenceLinks';

/** A recorded value with its label; the tone repeats what the label and value say. */
function Signal({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <span className="evidence-signal" data-tone={tone}>
      <span className="evidence-signal-label">{label}</span>
      <span>{value}</span>
    </span>
  );
}

function known(value: string | null | undefined): string {
  return value?.trim() ? value : 'Unknown';
}

function time(value: string | null | undefined): string {
  return value && Number.isFinite(Date.parse(value)) ? formatUtc(value) : 'Unknown';
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="min-w-0">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{title}</h3>
      <dl className="mt-2 grid min-w-0 gap-x-6 gap-y-3 sm:grid-cols-2">{children}</dl>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm [overflow-wrap:anywhere]">{children}</dd>
    </div>
  );
}

function Prose({ title, text }: { title: string; text: string }) {
  return (
    <div className="min-w-0">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{title}</h3>
      <p dir="auto" className="mt-1 whitespace-pre-wrap text-sm leading-6 [overflow-wrap:anywhere]">
        {text}
      </p>
    </div>
  );
}

/** One frozen source: a scannable summary row, then its grouped recorded metadata. */
export function EvidenceItemDetails({
  item,
  assessment,
}: {
  item: EvidenceItem;
  assessment: EvidenceAssessment | undefined;
}) {
  return (
    <details id={evidenceId(item.label)} className="scroll-mt-6 border-b border-line">
      <summary className="cursor-pointer rounded px-1 py-3 text-sm transition-colors hover:bg-surface-2/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ember motion-reduce:transition-none">
        <span className="ml-2 inline-grid w-[calc(100%-2rem)] grid-cols-[2.5rem_minmax(0,1fr)_auto] gap-3 align-top">
          <span className="font-mono text-xs font-semibold text-ember">{item.label}</span>
          <span className="min-w-0">
            <span
              dir="auto"
              className="block whitespace-pre-wrap font-medium leading-6 [overflow-wrap:anywhere]"
            >
              {item.title}
            </span>
            <span className="mt-1 block text-xs text-muted [overflow-wrap:anywhere]">
              {item.source_name} ·{' '}
              {item.observation
                ? `Acquired ${time(item.observation.acquired_at)}`
                : time(item.published_at)}
            </span>
          </span>
          <span
            className="evidence-grade self-start"
            data-tone={gradeTone(item.grade)}
            title="Source reliability letter and information credibility number"
          >
            <span className="sr-only">Grade </span>
            {item.grade}
          </span>
        </span>
      </summary>
      <div className="flex min-w-0 flex-col gap-5 pb-6 pl-4 pr-1 sm:pl-12">
        {item.title_en && <Prose title="Translation (unverified)" text={item.title_en} />}
        {item.summary && <Prose title="Original source snippet" text={item.summary} />}
        {assessment && (
          <Group title="Automated assessment">
            <Field label="Contribution">
              <span className="font-mono capitalize">{assessment.contribution}</span>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-muted">
                {assessment.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </Field>
          </Group>
        )}
        <Group title="Grading">
          <Field label="Reliability and credibility">
            <span className="flex flex-wrap gap-2">
              <Signal
                label="Reliability"
                value={item.reliability ?? 'Unknown'}
                tone={reliabilityTone(item.reliability)}
              />
              <Signal
                label="Credibility"
                value={item.credibility == null ? 'Unknown' : String(item.credibility)}
                tone={credibilityTone(item.credibility)}
              />
            </span>
          </Field>
          <Field label="Grade rationale">{item.grade_rationale || 'Not provided'}</Field>
        </Group>
        <Group title="Timing (UTC)">
          <Field label="Published">{time(item.published_at)}</Field>
          <Field label="Observed">{time(item.observed_at)}</Field>
          <Field label="Captured">{time(item.captured_at)}</Field>
          <Field label="Language">{known(item.language)}</Field>
        </Group>
        <Group title="Place and origin">
          <Field label="Country">{known(item.country_iso)}</Field>
          <Field label="Location precision">{known(item.geo_confidence)}</Field>
          <Field label="Coordinates (longitude, latitude)">
            {item.lon == null || item.lat == null
              ? 'Unknown'
              : `${String(item.lon)}, ${String(item.lat)}`}
          </Field>
          <Field label="Declared organisation">{known(item.independence_key)}</Field>
        </Group>
        <SourceProvenanceDetails transformations={item.transformations} dates={item.source_dates} />
        <EvidenceProjectDetails item={item} />
        <EvidenceObservationDetails item={item} />
        <SourceRatingDetails rating={item.source_rating} frozen />
        <details className="min-w-0 text-xs">
          <summary className="cursor-pointer py-2 font-medium">Identifiers and integrity</summary>
          <dl className="mt-2 grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <Field label="Source ID">{item.source_id}</Field>
            <Field label="Topic cluster">{known(item.story_id)}</Field>
            <Field label="Event ID">
              <span className="font-mono text-xs">{item.event_id}</span>
            </Field>
            <Field label="Content hash">
              <span className="font-mono text-xs">{known(item.content_hash)}</span>
            </Field>
          </dl>
        </details>
        <details className="min-w-0 text-xs">
          <summary className="cursor-pointer py-2 font-medium">Retained source attributes</summary>
          {item.attributes?.length ? (
            <dl className="mt-2 space-y-3 [overflow-wrap:anywhere]">
              {item.attributes.map((attribute, index) => (
                <div key={index}>
                  <dt className="font-mono text-muted">{attribute.key}</dt>
                  <dd className="mt-1 whitespace-pre-wrap">
                    {attribute.value === null ? 'Not recorded (null)' : String(attribute.value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-2 text-muted">No source attributes recorded for this version.</p>
          )}
        </details>
        {item.flags.length > 0 && (
          <div className="min-w-0">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
              Recorded source flags
            </h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {item.flags.map((flag) => (
                <Signal key={flag} label="Flag" value={flagLabel(flag)} tone={flagTone(flag)} />
              ))}
            </div>
          </div>
        )}
        <p className="text-xs leading-5 text-muted">
          Independent sourcing is not verified; topic grouping does not establish corroboration.
          Coordinates reflect the recorded location precision.
        </p>
        <div className="flex flex-wrap gap-4 text-xs">
          <SourceLink url={item.url}>Open source</SourceLink>
          <SourceLink url={item.archive_url}>Open archive</SourceLink>
        </div>
      </div>
    </details>
  );
}
