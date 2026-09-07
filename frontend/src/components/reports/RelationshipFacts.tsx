import type { RelationshipAssertion } from '@/lib/api/relationships';
import { Labels } from './EvidenceLinks';
const metadata = [
  ['reported_relationship_status', 'Source relationship status'],
  ['reported_valid_from', 'Source record valid from'],
  ['reported_valid_to', 'Source record valid to'],
  ['reported_last_update', 'Registry last update'],
  ['reported_registration_status', 'Source registration status'],
] as const;
const original = (value: unknown) =>
  typeof value === 'string' && value.trim() ? value : 'Not recorded';
export function RelationshipFacts({ value }: { value: RelationshipAssertion }) {
  const attrs = new Map(value.attributes.map((item) => [item.key, item.value]));
  const omitted = attrs.get('reported_periods_omitted');
  return (
    <section
      aria-label="Frozen source relationship"
      className="space-y-3 border-l-2 border-ember/50 pl-4 text-xs [overflow-wrap:anywhere]"
    >
      <h4 className="font-medium">Source-reported {value.kind} accounting-consolidation parent</h4>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-muted">Child LEI</dt>
          <dd className="font-mono">{value.child_lei}</dd>
        </div>
        <div>
          <dt className="text-muted">Reported parent LEI</dt>
          <dd className="font-mono">{value.parent_lei}</dd>
        </div>
        <div>
          <dt className="text-muted">Original relationship type</dt>
          <dd>{value.relationship_type}</dd>
        </div>
        <div>
          <dt className="text-muted">Evidence captured</dt>
          <dd>{value.captured_at}</dd>
        </div>
        <div>
          <dt className="text-muted">Publication time</dt>
          <dd>{value.published_at ?? 'Not recorded'}</dd>
        </div>
        {metadata.map(([key, label]) => (
          <div key={key}>
            <dt className="text-muted">{label}</dt>
            <dd>{original(attrs.get(key))}</dd>
          </div>
        ))}
      </dl>
      <p>
        Frozen source: {value.source_id} <Labels labels={[value.evidence_label]} />
      </p>
      <div>
        <h5 className="font-medium">Source-reported periods, original values</h5>
        {value.periods_state !== 'parsed' ? (
          <p>Period metadata is {value.periods_state}. Current validity is unknown.</p>
        ) : value.periods?.length ? (
          <ul>
            {value.periods.map((period, index) => (
              <li key={index}>
                {original(period.type)}: {original(period.startDate)} to {original(period.endDate)}
              </li>
            ))}
          </ul>
        ) : (
          <p>No periods were captured. Current validity is unknown.</p>
        )}
        {typeof omitted === 'number' && omitted > 0 && (
          <p>{omitted} period entries were omitted during collection.</p>
        )}
      </div>
      <p className="text-muted">
        Accounting consolidation does not establish beneficial ownership or an identity match.
        Source periods, publication, capture and review dates describe different events; none alone
        establishes current validity.
      </p>
      <details>
        <summary className="cursor-pointer py-2">Original assertion attributes</summary>
        <dl className="space-y-2">
          {value.attributes.map((item, index) => (
            <div key={index}>
              <dt className="font-mono">{item.key}</dt>
              <dd>{item.value === null ? 'Not recorded (null)' : String(item.value)}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}
