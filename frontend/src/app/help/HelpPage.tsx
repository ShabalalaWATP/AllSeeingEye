/**
 * The in-app user guide. The repository's reader guides are not served by the app, so
 * this page summarises the core loop as structured text, names every workspace exactly
 * as navigation does, and can show the Start here card again. It renders fixed React
 * text only; nothing here is HTML from data and nothing starts work.
 */
import { useEffect, useId, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { workspaceDestinations, workspaceHome } from '@/lib/workspaceNavigation';

import { Glossary } from './Glossary';

import { StartHereSteps } from './StartHereCard';
import { useStartHere } from './useStartHere';

const CORE_LOOP: readonly (readonly [title: string, detail: string])[] = [
  [
    'Explore an observation',
    'Choose the globe or flat map, turn on the layers you need and open an item. Check its source, date, grade and location precision before treating a marker as an exact location.',
  ],
  [
    'Ask a bounded question',
    'In Research, write the question, then choose the focus, depth, places, period and a personal or team destination. A long period does not give every source a historical archive.',
  ],
  [
    'Review the answer and its evidence',
    'Follow the run in Research progress, then read the findings beside their citations, evidence annex, collection gaps and confidence limits. A saved version keeps the evidence it used.',
  ],
  [
    'Follow a subject over time',
    'In Subscriptions, under Watches, run the same question on a schedule. Each update is saved with its own status. Pause a subscription to stop future work.',
  ],
  [
    'Watch and share',
    'Use Alerts, Plans and areas and Annotation monitors under Watches for standing checks, and Teams to share work with current members.',
  ],
];

function Section({ title, children, id }: { title: string; children: ReactNode; id?: string }) {
  const headingId = useId();
  return (
    <section id={id} aria-labelledby={headingId} className="scroll-mt-6 space-y-3">
      <h2 id={headingId} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function HelpPage() {
  const { reopen } = useStartHere();
  const navigate = useNavigate();
  const { hash } = useLocation();
  useEffect(() => {
    // Links such as /help#glossary-source-grades land on the explanation they name.
    const target = hash ? document.getElementById(decodeURIComponent(hash.slice(1))) : null;
    const scroll: unknown = target ? Reflect.get(target, 'scrollIntoView') : undefined;
    if (target && typeof scroll === 'function') scroll.call(target, { block: 'start' });
  }, [hash]);
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-3xl space-y-8 pb-24">
        <PageHeader
          title="Help and guide"
          description="The app connects a live picture to research you can revisit. Notice something on the map, research a question, inspect the answer's evidence, then save, repeat or watch the work when it is useful."
        />

        <Section title="Start here">
          <StartHereSteps headingLevel="h3" />
          <Button
            variant="secondary"
            onClick={() => {
              reopen();
              void navigate(workspaceHome.to);
            }}
          >
            Show Start here again
          </Button>
        </Section>

        <Section title="The core loop">
          <ol aria-label="The core loop" className="space-y-3">
            {CORE_LOOP.map(([title, detail], index) => (
              <li key={title} className="rounded-card border border-line bg-surface p-3">
                <p className="text-sm font-semibold">
                  {index + 1}. {title}
                </p>
                <p className="mt-1 text-sm leading-6 text-muted">{detail}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section title="Where things are">
          <dl className="divide-y divide-line/70">
            {workspaceDestinations().map((destination) => (
              <div key={destination.to} className="grid gap-1 py-2 sm:grid-cols-[12rem_1fr]">
                <dt className="text-sm font-medium">{destination.label}</dt>
                <dd className="text-sm text-muted">{destination.description}</dd>
              </div>
            ))}
          </dl>
          <p className="text-sm text-muted">
            Administration is a separate workspace that only administrators see.
          </p>
        </Section>

        <Section title="Glossary" id="glossary">
          <Glossary />
        </Section>

        <Section title="Getting around faster">
          <p className="text-sm leading-6 text-muted">
            Press Ctrl K, or Cmd K on a Mac, to find any page, tracker or map layer by name. Press ?
            for the keyboard shortcuts.
          </p>
        </Section>
      </div>
    </section>
  );
}
