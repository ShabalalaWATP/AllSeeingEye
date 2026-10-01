/**
 * The updates a subscription has produced, listed beside the subscriptions themselves.
 */
import { Link } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { SectionTabs, subscriptionTabs } from '@/components/research/SectionTabs';

import { SavedReports } from './SavedReports';

export default function SavedUpdatesPage() {
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <SectionTabs tabs={subscriptionTabs} label="Subscriptions" />
      <PageHeader
        title="Saved updates"
        description="Every edition your subscriptions have produced, newest first. Each one states what changed since the previous update."
      >
        <Link to="/reports/saved" className="w-fit text-sm text-muted underline hover:text-text">
          All saved reports
        </Link>
      </PageHeader>
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
