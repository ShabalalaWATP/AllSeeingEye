import type { EvidenceItem } from '@/lib/api/reports';
import { Labels } from './EvidenceLinks';
import { organisationRelationships } from './organisationRelationships';
import type { ReportedRelationship } from './organisationRelationships';

const metadata = [
  ['reported_relationship_status', 'Relationship status'],
  ['reported_valid_from', 'Record valid from'],
  ['reported_valid_to', 'Record valid to'],
  ['reported_last_update', 'Registry last update'],
  ['reported_registration_status', 'Registration status'],
  ['reported_corroboration_level', 'Source-reported corroboration'],
  ['reported_corroboration_documents', 'Source-reported documents'],
  ['reported_corroboration_reference', 'Source-reported reference'],
] as const;
const original = (value: unknown) =>
  typeof value === 'string' && value.trim() ? value : 'Not recorded';

function Relationship({ row }: { row: ReportedRelationship }) {
  const omitted = row.attributes.get('reported_periods_omitted');
  return (
    <article className="space-y-3 border-l-2 border-ember/50 py-2 pl-4 text-sm [overflow-wrap:anywhere]">
      <h3 className="font-medium">Reported {row.kind} accounting-consolidation parent</h3>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-muted">Child LEI</dt>
          <dd className="font-mono">{row.child}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Reported parent LEI</dt>
          <dd className="font-mono">{row.parent}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted">
        Source assertion · {row.evidence.source_name} · Captured grade {row.evidence.grade}
        <Labels labels={[row.evidence.label]} />
      </p>
      <dl className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-muted">Evidence captured</dt>
          <dd>{original(row.evidence.captured_at)}</dd>
        </div>
        {metadata.map(([key, label]) => (
          <div key={key}>
            <dt className="text-muted">{label}</dt>
            <dd>{original(row.attributes.get(key))}</dd>
          </div>
        ))}
      </dl>
      <div>
        <h4 className="text-xs font-medium">Reported periods (original values)</h4>
        {row.periods?.length ? (
          <ul className="mt-2 space-y-2 text-xs">
            {row.periods.map((period, index) => (
              <li key={index}>
                {original(period.type)}: {original(period.startDate)} to {original(period.endDate)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-muted">
            {row.periods === null
              ? 'Period metadata is missing or unreadable; inspect the original evidence.'
              : 'No periods were captured.'}
          </p>
        )}
        {typeof omitted === 'number' && Number.isInteger(omitted) && omitted > 0 && (
          <p className="mt-2 text-xs text-muted">
            {omitted} period entries were omitted during collection.
          </p>
        )}
      </div>
    </article>
  );
}

export function ReportedRelationships({ evidence }: { evidence: readonly EvidenceItem[] }) {
  const { rows, unusable } = organisationRelationships(evidence);
  return (
    <details className="min-w-0 border-t border-line py-3">
      <summary className="cursor-pointer py-2 font-medium">
        Reported organisation relationships ({rows.length})
      </summary>
      <div className="mt-3 space-y-5">
        <p className="text-sm text-muted">
          GLEIF source assertions captured in this report version. Accounting consolidation does not
          independently establish beneficial ownership. Direct and ultimate parents remain separate;
          no additional connections or identity matches are inferred. Original dates may describe
          different record or relationship periods and do not establish current status.
        </p>
        {rows.length === 0 && (
          <p className="text-sm text-muted">
            No usable GLEIF parent assertions were captured. This does not establish that no parent
            exists.
          </p>
        )}
        {unusable.length > 0 && (
          <p className="text-sm text-muted">
            Some captured relationship records could not be displayed safely. Inspect their original
            attributes:
            <Labels labels={unusable} />
          </p>
        )}
        {rows.map((row, index) => (
          <Relationship key={`${row.evidence.label}:${index}`} row={row} />
        ))}
      </div>
    </details>
  );
}
