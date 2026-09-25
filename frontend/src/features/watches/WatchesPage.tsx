import { Link } from 'react-router';

import { useWatches } from './useWatches';
import { WatchGroupCard } from './WatchGroupCard';

/** The home of every standing watch: one card per kind, each linking to its own page. */
export default function WatchesPage() {
  const groups = useWatches();
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-6 sm:px-7 lg:px-10">
      <div className="mx-auto max-w-6xl space-y-6 pb-24">
        <header className="max-w-3xl">
          <h1 className="text-xl font-semibold">Watches</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Everything you and your teams are watching, in one place. Each card counts one kind of
            watch and lists the most recently changed. What your watches raise appears in{' '}
            <Link to="/warning" className="text-text underline">
              Alerts
            </Link>
            .
          </p>
        </header>
        <ul aria-label="Kinds of watch" className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {groups.map((group) => (
            <WatchGroupCard key={group.kind} group={group} />
          ))}
        </ul>
      </div>
    </section>
  );
}
