import { registryLabels } from '@/lib/api/registryRouting';
import type { RegistryLookup } from '@/lib/api/registryRouting';

export function RegistryLookupDetails({
  value,
  candidateLabel,
}: {
  value: RegistryLookup;
  candidateLabel?: string | undefined;
}) {
  return (
    <section
      className="space-y-1 rounded border border-line p-3 text-xs [overflow-wrap:anywhere]"
      aria-label="Exact registry lookup"
    >
      <p className="font-medium text-cyan">Exact {registryLabels[value.namespace]} lookup</p>
      <dl className="grid gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-muted">Candidate hypothesis</dt>
          <dd>{candidateLabel ?? value.candidate_id}</dd>
        </div>
        <div>
          <dt className="text-muted">Registry namespace</dt>
          <dd>{registryLabels[value.namespace]}</dd>
        </div>
        <div>
          <dt className="text-muted">Original identifier</dt>
          <dd dir="auto">{value.original_value}</dd>
        </div>
        <div>
          <dt className="text-muted">Canonical lookup subject</dt>
          <dd className="font-mono">{value.subject}</dd>
        </div>
      </dl>
      <p className="text-muted">
        Operator-supplied identifier, retained without translation. This checks a candidate; it does
        not establish an identity match or independently search for conflicting evidence.
      </p>
    </section>
  );
}
