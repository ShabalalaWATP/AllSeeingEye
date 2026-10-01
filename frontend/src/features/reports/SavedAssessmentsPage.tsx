/**
 * The geolocation assessments this operator has saved, beside the tool that makes them.
 */
import { Link } from 'react-router';

import { PageHeader } from '@/components/ui/PageHeader';
import { geolocationTabs, SectionTabs } from '@/components/research/SectionTabs';

import { SavedReports } from './SavedReports';

export default function SavedAssessmentsPage() {
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <SectionTabs tabs={geolocationTabs} label="Geolocation" />
      <PageHeader
        title="Saved assessments"
        description="Photograph assessments and the candidate locations each one considered, with the evidence frozen as it was read."
      >
        <Link to="/reports/saved" className="w-fit text-sm text-muted underline hover:text-text">
          All saved reports
        </Link>
      </PageHeader>
      <SavedReports
        origin="geolocation"
        caption="Saved geolocation assessments"
        empty="No assessments yet. Upload a photograph to assess where it was taken."
      />
      <Link to="/geolocation" className="text-sm text-muted underline hover:text-text">
        Assess another photograph
      </Link>
    </section>
  );
}
