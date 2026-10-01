import { useId } from 'react';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { START_HERE_STEPS } from '@/lib/startHere';
import { helpDestination } from '@/lib/workspaceNavigation';

import { useStartHere } from './useStartHere';

/** The three Start here steps; every link only opens a page. */
export function StartHereSteps({ headingLevel }: { headingLevel: 'h3' | 'h4' }) {
  const Heading = headingLevel;
  return (
    <ol className="space-y-3">
      {START_HERE_STEPS.map((step, index) => (
        <li key={step.title} className="flex gap-3">
          <span
            aria-hidden="true"
            className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border border-line font-mono text-xs text-muted"
          >
            {index + 1}
          </span>
          <div className="min-w-0">
            <Heading className="text-sm font-semibold">{step.title}</Heading>
            <p className="mt-0.5 text-xs leading-5 text-muted">{step.detail}</p>
            <Link to={step.to} className="text-sm text-ember underline underline-offset-2">
              {step.linkLabel}
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}

/**
 * Orientation for an account's first visits to the map, until that account dismisses
 * it. Help can show it again. It never starts research, collection or a model call.
 */
export function StartHereCard() {
  const { visible, dismiss } = useStartHere();
  const headingId = useId();
  if (!visible) return null;
  return (
    <aside
      aria-labelledby={headingId}
      className="absolute bottom-4 left-4 z-30 max-h-[calc(100%-2rem)] w-[min(23rem,calc(100%-2rem))] overflow-y-auto rounded-xl border border-line bg-ground/95 p-4 text-text shadow-card backdrop-blur"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-2xs tracking-[0.18em] text-muted uppercase">New here</p>
          <h2 id={headingId} className="text-base font-semibold">
            Start here
          </h2>
        </div>
        {/* The visible word starts the name, so speech users can say "Dismiss". */}
        <Button
          variant="ghost"
          className="min-h-11"
          aria-label="Dismiss Start here"
          onClick={dismiss}
        >
          Dismiss
        </Button>
      </div>
      <StartHereSteps headingLevel="h3" />
      <p className="mt-4 border-t border-line/70 pt-3 text-sm">
        <Link to={helpDestination.to} className="text-ember underline underline-offset-2">
          Read the user guide
        </Link>
        <span className="text-muted"> · You can reopen this card from Help.</span>
      </p>
    </aside>
  );
}
