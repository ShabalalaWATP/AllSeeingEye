import type { SourceDate, TextTransformation } from '@/lib/api/sourceProvenance';

export function SourceProvenanceDetails({
  transformations = [],
  dates = [],
}: {
  transformations?: TextTransformation[] | undefined;
  dates?: SourceDate[] | undefined;
}) {
  if (!transformations.length && !dates.length) return null;
  return (
    <section
      className="space-y-4 text-xs [overflow-wrap:anywhere]"
      aria-label="Source language and date provenance"
    >
      {transformations.map((value, index) => (
        <article key={`text:${index}`} className="space-y-2 rounded border border-line p-3">
          <h3 className="font-medium capitalize">
            {value.kind} of original {value.field}
          </h3>
          <dl className="space-y-2">
            <div>
              <dt className="text-muted">
                Original text ({value.source_language}
                {value.source_script ? ` / ${value.source_script}` : ''})
              </dt>
              <dd dir="auto" className="whitespace-pre-wrap">
                {value.original_text}
              </dd>
            </div>
            <div>
              <dt className="text-muted">
                {value.kind === 'translation' ? 'Translated' : 'Transliterated'} text (
                {value.target_language}
                {value.target_script ? ` / ${value.target_script}` : ''})
              </dt>
              <dd dir="auto" className="whitespace-pre-wrap">
                {value.transformed_text}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Provenance / method</dt>
              <dd>
                {value.origin} / {value.method}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Review state</dt>
              <dd>
                {value.review_status === 'operator_declared'
                  ? 'Operator declaration, not independent verification'
                  : 'Unreviewed'}
              </dd>
            </div>
            {(value.model ?? value.provider ?? value.profile_id) && (
              <div>
                <dt className="text-muted">Recorded translation connection</dt>
                <dd>
                  {[value.provider, value.model, value.profile_id].filter(Boolean).join(' / ')}
                </dd>
              </div>
            )}
            {value.actor_id && (
              <div>
                <dt className="text-muted">Declared by</dt>
                <dd>{value.actor_id}</dd>
              </div>
            )}
          </dl>
          <p className="text-muted">
            A transformation does not establish equivalent meaning, pronunciation or identity.
          </p>
          {!!value.limitations.length && (
            <ul className="list-disc pl-4">
              {value.limitations.map((text, position) => (
                <li key={position}>{text}</li>
              ))}
            </ul>
          )}
        </article>
      ))}
      {dates.map((value, index) => (
        <article key={`date:${index}`} className="space-y-2 rounded border border-line p-3">
          <h3 className="font-medium">Declared source date: {value.role.replace(/_/g, ' ')}</h3>
          <dl className="grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-muted">Raw source date</dt>
              <dd dir="auto" className="whitespace-pre-wrap">
                {value.raw_text}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Source field</dt>
              <dd>{value.field}</dd>
            </div>
            <div>
              <dt className="text-muted">Declared calendar</dt>
              <dd>
                {value.calendar === 'solar_hijri_icu33'
                  ? 'Solar Hijri, ICU33 arithmetic convention'
                  : value.calendar}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Declaration basis</dt>
              <dd>{value.basis.replace(/_/g, ' ')}</dd>
            </div>
            <div>
              <dt className="text-muted">Resolution / precision</dt>
              <dd>
                {value.status} / {value.precision}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Conversion method</dt>
              <dd>{value.method}</dd>
            </div>
            {value.actor_id && (
              <div>
                <dt className="text-muted">Date declared by</dt>
                <dd>{value.actor_id}</dd>
              </div>
            )}
            {value.value && (
              <div>
                <dt className="text-muted">Resolved instant (explicit offset)</dt>
                <dd>{value.value}</dd>
              </div>
            )}
            {value.day_start && (
              <div>
                <dt className="text-muted">Resolved calendar date interval</dt>
                <dd>
                  {value.day_start} to {value.day_end} (end excluded). Date precision only; timezone
                  unknown.
                </dd>
              </div>
            )}
          </dl>
          <p className="text-muted">
            This declaration is separate from capture time. Record validity is not an occurrence
            date.
          </p>
          {!!value.limitations.length && (
            <ul className="list-disc pl-4">
              {value.limitations.map((text, position) => (
                <li key={position}>{text}</li>
              ))}
            </ul>
          )}
        </article>
      ))}
    </section>
  );
}
