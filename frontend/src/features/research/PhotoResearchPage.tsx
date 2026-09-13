import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { PhotoGeolocationPanel } from './PhotoGeolocationPanel';

const STEPS = [
  {
    title: 'Add up to six photographs',
    detail: 'Originals are discarded after extraction; sanitised previews expire in 15 minutes.',
  },
  {
    title: 'Add context, then consent',
    detail: 'Hints are claims to test. Nothing is sent until you tick the consent box.',
  },
  {
    title: 'Assess candidates, then save',
    detail: 'Every location is a hypothesis with its own contradictions and verification steps.',
  },
] as const;

export default function PhotoResearchPage() {
  const workspaces = useWorkspaces();
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-6xl space-y-8 pb-24">
        <header className="relative overflow-hidden rounded-2xl border border-line/70 bg-surface/50 px-5 py-6 sm:px-7">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_80%_at_100%_0%,color-mix(in_srgb,var(--color-cyan)_12%,transparent),transparent_70%)]"
          />
          <div className="relative grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-end">
            <div>
              <p className="mb-2 font-mono text-[10px] tracking-[0.22em] text-cyan uppercase">
                Visual research
              </p>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Geolocation</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
                Compare photographs, examine visible clues and assess possible locations. Save the
                findings with supporting evidence and the checks still needed.
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
        <PhotoGeolocationPanel key={workspaces.key} workspaces={workspaces} />
      </div>
    </section>
  );
}
