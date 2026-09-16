import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import type { ExplainerSection, ExplainerStatus } from '@/lib/api/economyExplainer';
import { ExplainerBadge, ExplainerProvenanceNote } from './ExplainerProvenance';
import { regionExplainer } from './explainerModel';
import type { EconomyExplainerState } from './useEconomyExplainer';

const TITLE = 'The world economy right now';

export function PointList({
  title,
  items,
  tone,
}: {
  title: string;
  items: readonly string[];
  tone: 'ember' | 'muted';
}) {
  if (items.length === 0) return null;
  return (
    <section aria-label={title} className="min-w-0">
      <h3
        className={`mb-2 font-mono text-[10px] tracking-[0.18em] uppercase ${tone === 'ember' ? 'text-ember' : 'text-muted'}`}
      >
        {title}
      </h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="border-l-2 border-line pl-3 text-[13px] leading-6 text-text/90">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The takeaway leads, the paragraphs explain, and the short lists sit alongside. */
export function ExplainerBody({ section }: { section: ExplainerSection }) {
  return (
    <div className="grid gap-x-12 gap-y-7 xl:grid-cols-[minmax(0,1fr)_minmax(240px,300px)]">
      <div className="min-w-0 space-y-5">
        <p className="max-w-[44ch] border-l-2 border-ember pl-4 text-xl leading-8 font-medium text-balance sm:text-[22px] sm:leading-9">
          {section.takeaway}
        </p>
        <div className="max-w-[68ch] space-y-4">
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph} className="text-[15px] leading-7 text-text/90">
              {paragraph}
            </p>
          ))}
        </div>
      </div>
      <div className="grid gap-6 border-t border-line pt-5 sm:grid-cols-2 xl:grid-cols-1 xl:border-t-0 xl:pt-0">
        <PointList title="What is driving it" items={section.drivers} tone="ember" />
        <PointList title="What to watch" items={section.watch} tone="muted" />
      </div>
    </div>
  );
}

export function WorldExplainer({ state }: { state: EconomyExplainerState }) {
  const view = regionExplainer(state.data, 'WORLD');
  const refresh = state.isAdmin ? () => void state.forceRefresh() : undefined;
  return (
    <section
      aria-label={TITLE}
      className="rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7 sm:py-7"
    >
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="mb-1 font-mono text-[10px] tracking-[0.22em] text-ember uppercase">
            In plain English
          </p>
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">{TITLE}</h2>
        </div>
        <ExplainerBadge status={view.status} />
      </header>
      {state.loading && !state.data && <LoadingNote label="Loading the plain-English summary" />}
      {state.error && (
        <Alert tone="error">
          {describeError(state.error)}{' '}
          <Button variant="ghost" onClick={() => void state.reload()}>
            Retry summary
          </Button>
        </Alert>
      )}
      {view.section ? (
        <ExplainerBody section={view.section} />
      ) : (
        !state.loading &&
        !state.error && <ExplainerAbsence status={view.status} reason={view.reason} />
      )}
      {state.refreshError && (
        <Alert tone="warning" className="mt-4">
          {describeError(state.refreshError)}
        </Alert>
      )}
      <div className="mt-6">
        <ExplainerProvenanceNote
          status={view.status}
          provenance={view.provenance}
          isAdmin={state.isAdmin}
          refreshing={state.refreshing}
          onRefresh={refresh}
        />
      </div>
    </section>
  );
}

export function ExplainerAbsence({
  status,
  reason,
}: {
  status: ExplainerStatus;
  reason: string | null;
}) {
  const tone = status === 'validation_failed' || status === 'unavailable' ? 'warning' : 'info';
  const fallback =
    status === 'generating'
      ? 'A plain-English summary is being written from the current figures. The figures on this page are already up to date.'
      : 'No plain-English summary has been written yet. The figures on this page are unaffected.';
  return (
    <Alert tone={tone}>
      {reason ?? fallback}
      {status === 'validation_failed'
        ? ' Only the figures are shown until a summary passes the checks.'
        : ''}
    </Alert>
  );
}
