/**
 * The Research section's own saved reports, with the tools that belong to them:
 * semantic search, the reading library and the specialist templates.
 */
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { ResearchLibrary } from '@/components/library/ResearchLibrary';
import { researchTabs, SectionTabs } from '@/components/research/SectionTabs';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';

import { ReportSearch } from './ReportSearch';
import { SavedReports } from './SavedReports';
import { TemplateReportComposer } from './TemplateReportComposer';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function SavedResearchPage() {
  const [params] = useSearchParams();
  const [libraryRevision, setLibraryRevision] = useState(0);
  const libraryChanged = () => setLibraryRevision((revision) => revision + 1);
  const [showComposer, setShowComposer] = useState(false);
  const [closedContext, setClosedContext] = useState<string | null>(null);
  // Old "Generate assessment" bookmarks pointed here; plan assessments now start in Research.
  const legacyPlan = params.get('template') === 'ask' ? params.get('plan') : null;
  const initial = Object.fromEntries(
    ['template', 'country', 'conflict', 'hazard', 'plan']
      .filter((key) => legacyPlan === null || (key !== 'template' && key !== 'plan'))
      .map((key) => [key, params.get(key)])
      .filter((entry): entry is [string, string] => entry[1] !== null),
  );
  const composerVisible =
    showComposer || (Object.keys(initial).length > 0 && closedContext !== params.toString());
  return (
    <section className="flex h-full flex-col gap-4 overflow-y-auto p-6">
      <SectionTabs tabs={researchTabs} label="Research" />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Saved research</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">
            Questions you have asked, their frozen evidence, comparisons and exports.
          </p>
          <Link to="/reports/saved" className="text-sm text-muted underline hover:text-text">
            All saved reports
          </Link>
        </div>
        <Link
          to="/research"
          className="rounded-md bg-ember px-4 py-3 text-sm font-medium text-ground"
        >
          New research
        </Link>
      </header>
      {legacyPlan !== null && (
        <Alert tone="info" title="Collection-plan assessments have moved to Research">
          Review the plan&apos;s requirements and scope there, then start the research yourself.{' '}
          {UUID.test(legacyPlan) ? (
            <Link
              className="text-ember underline"
              to={`/research?brief=new&plan=${encodeURIComponent(legacyPlan)}`}
            >
              Continue in Research with this plan
            </Link>
          ) : (
            'This link does not name a valid plan. Open the plan from Plans and areas instead.'
          )}{' '}
          Specialist report templates remain available below.
        </Alert>
      )}
      <div className="flex flex-wrap gap-4 text-sm">
        <Button
          variant="ghost"
          aria-expanded={composerVisible}
          onClick={() => {
            setShowComposer(!composerVisible);
            if (composerVisible) setClosedContext(params.toString());
          }}
        >
          Specialist report templates
        </Button>
      </div>
      <ReportSearch />
      <ResearchLibrary revision={libraryRevision} onChanged={libraryChanged} />
      {composerVisible && <TemplateReportComposer initial={initial} />}
      <SavedReports
        origin="research"
        caption="Saved research"
        empty="No saved research yet. Ask a question to create your first report."
        onChanged={libraryChanged}
      />
    </section>
  );
}
