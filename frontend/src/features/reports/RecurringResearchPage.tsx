import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchPlans } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { fetchCountries } from '@/lib/api/geo';
import { fetchTemplates } from '@/lib/api/reports';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useSearchParams } from 'react-router';

import { SchedulesSection } from './SchedulesSection';

async function loadOptions() {
  const [templates, plans, countries] = await Promise.all([
    fetchTemplates(),
    fetchPlans(),
    fetchCountries(),
  ]);
  return { templates, plans, countries };
}

const STEPS = [
  {
    title: 'Choose what to follow',
    detail: 'A question, a conflict, a disaster or a saved area, in your personal or team space.',
  },
  {
    title: 'Set the depth and rhythm',
    detail: 'Basic, deep or advanced research, daily through annual, at the hour you choose.',
  },
  {
    title: 'Read what changed',
    detail:
      'Each run is a cited report. Change detection highlights new developments and links the previous update.',
  },
] as const;

export default function RecurringResearchPage() {
  const [params] = useSearchParams();
  const workspaces = useWorkspaces();
  const options = useScopedResource(loadOptions);
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-8 pb-24">
        <header className="relative overflow-hidden rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_100%_0%,color-mix(in_srgb,var(--color-ember)_12%,transparent),transparent_70%)]"
          />
          <div className="relative grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-end">
            <div>
              <p className="mb-2 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
                Standing research
              </p>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Subscriptions</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
                Follow a topic, conflict, disaster or area. Receive cited updates that prioritise
                what has changed, produced on the server as you at the hour you choose.
              </p>
            </div>
            <ol className="grid gap-2 text-xs sm:grid-cols-3 lg:grid-cols-1">
              {STEPS.map((step, index) => (
                <li
                  key={step.title}
                  className="flex gap-3 rounded-lg border border-line/60 bg-ground/40 px-3 py-2.5"
                >
                  <span className="font-mono text-[10px] text-ember">0{index + 1}</span>
                  <span>
                    <span className="block font-medium text-text">{step.title}</span>
                    <span className="mt-0.5 block leading-5 text-muted">{step.detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </header>
        {options.loading && <LoadingNote label="Loading subscriptions" />}
        {options.error && (
          <Alert tone="error">
            {describeError(options.error)}{' '}
            <Button variant="secondary" onClick={() => void options.reload()}>
              Retry options
            </Button>
          </Alert>
        )}
        {options.data && (
          <SchedulesSection
            key={`${workspaces.key}:${params.toString()}`}
            workspaces={workspaces}
            draftQuestion={(params.get('question') ?? '').slice(0, 1000)}
            draftCountry={
              options.data.countries.some((item) => item.iso2 === params.get('country'))
                ? (params.get('country') ?? '')
                : ''
            }
            {...options.data}
          />
        )}
      </div>
    </section>
  );
}
