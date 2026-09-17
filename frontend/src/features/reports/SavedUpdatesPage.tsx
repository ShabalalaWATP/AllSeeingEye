/**
 * The updates a subscription has produced, listed beside the subscriptions themselves.
 */
import { Link } from 'react-router';

import { SectionTabs, subscriptionTabs } from '@/components/research/SectionTabs';

import { SavedReports } from './SavedReports';

export default function SavedUpdatesPage() {
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <SectionTabs tabs={subscriptionTabs} label="Subscriptions" />
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Saved updates</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Every edition your subscriptions have produced, newest first. Each one states what changed
          since the previous update.
        </p>
      </header>
      <SavedReports
        origin="subscription"
        caption="Saved subscription updates"
        empty="No updates yet. A subscription saves its first edition when its next run is due."
      />
      <Link to="/subscriptions" className="text-sm text-muted underline hover:text-text">
        Manage subscriptions
      </Link>
    </section>
  );
}
