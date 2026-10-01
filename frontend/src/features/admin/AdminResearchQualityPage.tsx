import { AdminPage, AdminSection, EmptyState } from '@/components/admin/AdminPage';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { QUALITY_WINDOWS, type ResearchQuality } from '@/lib/api/researchQuality';
import { formatUtc } from '@/lib/format';

import { JobTable, VersionTable } from './quality/QualityTables';
import {
  DIMENSIONS,
  findingText,
  formatCount,
  jobCaption,
  jobGroups,
  plural,
  populationText,
  versionCaption,
  versionGroups,
  type QualityDimension,
} from './quality/qualityPresentation';
import { useResearchQuality } from './useResearchQuality';

function Toggle<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { id: T; label: string }[];
  value: T;
  onChange: (next: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1">
      {options.map((option) => (
        <Button
          key={option.id}
          variant={option.id === value ? 'secondary' : 'ghost'}
          aria-pressed={option.id === value}
          onClick={() => onChange(option.id)}
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}

function Populations({ data }: { data: ResearchQuality }) {
  return (
    <AdminSection title="Populations and bounds" icon="quality">
      <ul className="space-y-1 text-sm">
        <li>{populationText('saved version', data.versions, data.window_days)}</li>
        <li>{populationText('report job', data.jobs, data.window_days)}</li>
      </ul>
      <p className="mt-3 text-xs leading-5 text-muted">
        Each population counts at most the newest {formatCount(data.versions.bound)} rows saved or
        created since {formatUtc(data.since)}. Every saved version counts once by its saved status;
        every report job counts once by its job status, including failed jobs that never saved a
        version. The two populations are never added together. A missing template, depth or model is
        shown as Not recorded. Counts cover every report under existing administrator access and
        never include titles, report text or finding messages.
      </p>
    </AdminSection>
  );
}

function Details({ data }: { data: ResearchQuality }) {
  const overall = data.versions.overall;
  const { receipts } = overall;
  const jobs = data.jobs.overall;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <AdminSection title="Commonest validator findings" icon="alert">
        {overall.findings.length === 0 ? (
          <p className="text-sm text-muted">No validator findings in these versions.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {overall.findings.map((finding) => (
              <li key={finding.key} className="flex flex-wrap justify-between gap-x-4">
                <span className="font-mono text-xs">{`${finding.rule} (${finding.severity})`}</span>
                <span className="text-muted">
                  {findingText(finding.versions, finding.occurrences, overall.versions)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </AdminSection>
      <AdminSection title="Collection receipts" icon="sources">
        <ul className="space-y-1 text-sm">
          <li>{`Empty: ${formatCount(receipts.empty)} of ${plural(receipts.attempts, 'attempt')}`}</li>
          <li>{`Unavailable: ${formatCount(receipts.unavailable)} of ${plural(receipts.attempts, 'attempt')}`}</li>
          <li>{`Other unsuccessful: ${formatCount(receipts.other_unsuccessful)} of ${plural(receipts.attempts, 'attempt')}`}</li>
          <li>{`Without a research receipt: ${formatCount(receipts.versions_without_receipts)} of ${plural(overall.versions, 'version')}`}</li>
        </ul>
      </AdminSection>
      <AdminSection title="Job failure codes" icon="cross">
        {jobs.failure_codes.length === 0 ? (
          <p className="text-sm text-muted">No failure codes recorded.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {jobs.failure_codes.map((row) => (
              <li key={row.code} className="font-mono text-xs">
                {`${row.code}: ${formatCount(row.jobs)} of ${plural(jobs.failed, 'failed job')}`}
              </li>
            ))}
          </ul>
        )}
      </AdminSection>
      <AdminSection title="Citation checks" icon="check">
        <p className="text-sm text-muted">{data.citation_checks.note}</p>
      </AdminSection>
    </div>
  );
}

function Outcomes({ data, dimension }: { data: ResearchQuality; dimension: QualityDimension }) {
  return (
    <>
      <AdminSection title="Saved version outcomes" icon="audit">
        <VersionTable
          caption={versionCaption(dimension)}
          overall={data.versions.overall}
          groups={versionGroups(data, dimension)}
        />
      </AdminSection>
      <AdminSection title="Report job outcomes" icon="clock">
        <JobTable
          caption={jobCaption(dimension)}
          overall={data.jobs.overall}
          groups={jobGroups(data, dimension)}
        />
      </AdminSection>
    </>
  );
}

export default function AdminResearchQualityPage() {
  const quality = useResearchQuality();
  const { data } = quality;
  return (
    <AdminPage
      eyebrow="Research services"
      title="Research quality"
      description="Counts of saved report outcomes and report jobs, computed on request. Each figure names its denominator; no single rating is derived."
      actions={
        <Toggle
          label="Time window"
          options={QUALITY_WINDOWS.map((days) => ({ id: days, label: `${days} days` }))}
          value={quality.windowDays}
          onChange={quality.setWindowDays}
        />
      }
    >
      {quality.error === null ? null : (
        <Alert tone="error">
          {describeError(quality.error)}{' '}
          <Button variant="secondary" onClick={() => void quality.reload()}>
            Retry
          </Button>
        </Alert>
      )}
      {quality.loading && data === null ? <LoadingNote label="Loading research quality" /> : null}
      {data === null ? null : data.versions.in_window + data.jobs.in_window === 0 ? (
        <EmptyState icon="quality" title="No saved versions or report jobs in this window." />
      ) : (
        <>
          <Populations data={data} />
          <Toggle
            label="Group outcomes by"
            options={DIMENSIONS}
            value={quality.dimension}
            onChange={quality.setDimension}
          />
          <Outcomes data={data} dimension={quality.dimension} />
          <Details data={data} />
        </>
      )}
    </AdminPage>
  );
}
