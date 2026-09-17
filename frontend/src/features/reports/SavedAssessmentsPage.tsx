/**
 * The geolocation assessments this operator has saved, beside the tool that makes them.
 */
import { Link } from 'react-router';

import { geolocationTabs, SectionTabs } from '@/components/research/SectionTabs';

import { SavedReports } from './SavedReports';

export default function SavedAssessmentsPage() {
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <SectionTabs tabs={geolocationTabs} label="Geolocation" />
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Saved assessments</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          Photograph assessments and the candidate locations each one considered, with the evidence
          frozen as it was read.
        </p>
      </header>
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
