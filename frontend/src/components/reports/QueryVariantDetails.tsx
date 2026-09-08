import type { QueryVariant } from '@/lib/api/researchPlan';

export function QueryVariantDetails({ value }: { value: QueryVariant }) {
  return (
    <section
      aria-label="Query transformation provenance"
      className="space-y-2 rounded border border-line p-3 text-xs"
    >
      <h4 className="font-medium">
        {value.kind === 'transliteration'
          ? 'Operator-supplied transliteration'
          : 'Translation variant'}{' '}
        · {value.language}
      </h4>
      <p className="text-muted">
        {value.source_script ?? 'Source script not recorded'} to{' '}
        {value.target_script ?? 'Target script not recorded'} · Method:{' '}
        {value.method ?? 'Not recorded'}
      </p>
      <ul className="space-y-2">
        {value.terms.map((term, index) => (
          <li key={index}>
            <p className="text-muted" dir="auto">
              Original: {value.original_terms?.[index] ?? 'Original linkage not recorded'}
            </p>
            <p className="whitespace-pre-wrap [overflow-wrap:anywhere]" dir="auto">
              Exact outbound term: {term}
            </p>
          </li>
        ))}
      </ul>
      <p className="text-muted">
        Original text remains separate. Meaning, pronunciation and identity are not independently
        verified.
      </p>
    </section>
  );
}
