import type { EvidenceItem } from '@/lib/api/reports';

const yearLabel = (year: number | null) =>
  year === null ? 'Unknown' : `${year} (exact date unknown)`;

export function EvidenceProjectDetails({ item }: { item: EvidenceItem }) {
  const project = item.project;
  if (!project) return null;
  const amount = item.attributes?.find(
    (attribute) => attribute.key === 'aiddata_amount_constant_usd_2021',
  )?.value;
  const rows = [
    ['Project identifier', project.project_id],
    ['Dataset', project.dataset_id],
    ['Dataset release', project.release_id],
    ['Recipient country code', project.recipient_iso3],
    ['Source-reported status', project.reported_status],
    ...(project.dataset_id === 'aiddata-geogcdf'
      ? [['Reported amount (constant 2021 USD)', typeof amount === 'string' ? amount : 'Unknown']]
      : []),
    ['Commitment year', yearLabel(project.commitment_year)],
    ['Implementation year', yearLabel(project.implementation_year)],
    ['Completion year', yearLabel(project.completion_year)],
    ['Source precision', project.precision],
    ['Attribution', project.attribution],
    ['Data licence', project.data_licence],
    ['Geometry licence', project.geometry_licence],
  ];
  return (
    <section aria-label="Project record" className="min-w-0 border-l-2 border-line pl-4">
      <h3 className="text-sm font-medium">Project record</h3>
      <p className="mt-2 text-xs text-muted">
        These are historical source-reported facts. A commitment does not establish a payment, and a
        reported completion does not verify the project’s current condition.
      </p>
      <dl className="mt-3 grid gap-x-8 gap-y-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 text-sm [overflow-wrap:anywhere]">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted [overflow-wrap:anywhere]">{project.limitations}</p>
      <details className="mt-3 text-xs text-muted">
        <summary className="cursor-pointer py-2">Source integrity hash</summary>
        <p className="[overflow-wrap:anywhere]">SHA-256: {project.source_sha256}</p>
        <p className="mt-2">The hash identifies the source bytes, not their factual accuracy.</p>
      </details>
    </section>
  );
}
