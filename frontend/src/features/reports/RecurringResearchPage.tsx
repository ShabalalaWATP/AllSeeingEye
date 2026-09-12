import { ResearchNavigation } from '@/components/research/ResearchNavigation';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchPlans } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { fetchCountries } from '@/lib/api/geo';
import { fetchTemplates } from '@/lib/api/reports';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';

import { SchedulesSection } from './SchedulesSection';

async function loadOptions() {
  const [templates, plans, countries] = await Promise.all([
    fetchTemplates(),
    fetchPlans(),
    fetchCountries(),
  ]);
  return { templates, plans, countries };
}

export default function RecurringResearchPage() {
  const workspaces = useWorkspaces();
  const options = useScopedResource(loadOptions);
  return (
    <section className="h-full min-w-0 overflow-y-auto px-4 py-8 sm:px-8">
      <div className="mx-auto max-w-7xl space-y-7">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight">Scheduled research</h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
            Your regular research reports, delivered on a repeating schedule. Manage questions,
            report depth and timing in one place.
          </p>
        </header>
        <ResearchNavigation />
        {options.loading && <LoadingNote label="Loading recurring research" />}
        {options.error && (
          <Alert tone="error">
            {describeError(options.error)}{' '}
            <Button variant="secondary" onClick={() => void options.reload()}>
              Retry options
            </Button>
          </Alert>
        )}
        {options.data && (
          <SchedulesSection key={workspaces.key} workspaces={workspaces} {...options.data} />
        )}
      </div>
    </section>
  );
}
