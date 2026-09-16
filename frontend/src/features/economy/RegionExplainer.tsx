import { ExplainerBadge, ExplainerProvenanceNote } from './ExplainerProvenance';
import { PointList } from './WorldExplainer';
import type { RegionExplainerView } from './explainerModel';

/**
 * The plain-English words sit next to the figures they describe. The takeaway and the
 * first paragraph are always visible; anything longer is behind a native disclosure.
 */
export function RegionExplainer({ name, view }: { name: string; view: RegionExplainerView }) {
  const section = view.section;
  if (!section)
    return (
      <p className="border-l-2 border-line pl-4 text-sm leading-6 text-muted">
        {view.status === 'validation_failed'
          ? `The written summary for ${name} could not be checked against the figures, so it is not shown. The figures below are the source of truth.`
          : `No plain-English summary for ${name} is available yet. The figures below are unaffected.`}
      </p>
    );
  const [lead, ...rest] = section.paragraphs;
  return (
    <section
      aria-label={`${name} in plain English`}
      className="rounded-xl border border-line/70 bg-surface/40 px-4 py-5 sm:px-6"
    >
      <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-[10px] tracking-[0.22em] text-ember uppercase">
          {name} in plain English
        </p>
        <ExplainerBadge status={view.status} />
      </header>
      <p className="max-w-[50ch] border-l-2 border-ember pl-4 text-lg leading-8 font-medium text-balance">
        {section.takeaway}
      </p>
      {lead && <p className="mt-3 max-w-[68ch] text-[15px] leading-7 text-text/90">{lead}</p>}
      {rest.length > 0 && (
        <details className="group mt-3">
          <summary className="w-fit cursor-pointer text-sm font-medium text-muted hover:text-text focus-visible:outline-2 focus-visible:outline-ember">
            Read the rest
          </summary>
          <div className="mt-3 max-w-[68ch] space-y-4">
            {rest.map((paragraph) => (
              <p key={paragraph} className="text-[15px] leading-7 text-text/90">
                {paragraph}
              </p>
            ))}
          </div>
        </details>
      )}
      <div className="mt-5 grid gap-6 border-t border-line pt-4 sm:grid-cols-2">
        <PointList title="What is driving it" items={section.drivers} tone="ember" />
        <PointList title="What to watch" items={section.watch} tone="muted" />
      </div>
      <div className="mt-4">
        <ExplainerProvenanceNote status={view.status} provenance={view.provenance} compact />
      </div>
    </section>
  );
}
