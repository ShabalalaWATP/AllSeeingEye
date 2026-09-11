import { useCallback } from 'react';
import { useNavigate } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { fetchPlans } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { fetchCountries } from '@/lib/api/geo';
import { fetchTemplates, generateReport } from '@/lib/api/reports';
import type { ReportRequest } from '@/lib/api/reports';
import { fetchConflictBoard, fetchDisasterBoard } from '@/lib/api/trackers';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { useScopedResource } from '@/lib/hooks/useScopedResource';
import { useWorkspaces } from '@/lib/hooks/useWorkspaces';
import { useProfile } from '@/stores/profile';

import { GenerateForm } from './GenerateForm';

/** Specialist feed-based templates load only when the operator opens this tool. */
export function TemplateReportComposer({ initial }: { initial: Record<string, string> }) {
  const navigate = useNavigate();
  const preferences = useProfile();
  const workspaces = useWorkspaces();
  const templates = useScopedResource(fetchTemplates);
  const plans = useScopedResource(fetchPlans);
  const countries = useScopedResource(fetchCountries);
  const conflicts = useScopedResource(fetchConflictBoard);
  const hazards = useScopedResource(fetchDisasterBoard);
  const generate = useAsyncAction(
    useCallback(
      async (request: ReportRequest) => {
        const created = await generateReport(request);
        await navigate(`/reports/${created.report.id}`);
      },
      [navigate],
    ),
  );

  return (
    <div className="space-y-3 border-t border-line pt-4">
      <p className="text-sm text-muted">
        Create a structured product from retained feeds or a saved collection plan. Use Research for
        a fresh question across public sources.
      </p>
      {templates.loading && <LoadingNote label="Loading products" />}
      {[templates, plans, countries, conflicts, hazards].map((resource, index) =>
        resource.error ? (
          <Alert tone="error" key={index}>
            {describeError(resource.error)}
          </Alert>
        ) : null,
      )}
      {!preferences.profile && preferences.error && (
        <Alert tone="error">
          Report preferences could not be loaded.{' '}
          <Button variant="secondary" onClick={() => void preferences.reload()}>
            Retry preferences
          </Button>
        </Alert>
      )}
      {templates.data && preferences.profile && (
        <GenerateForm
          key={`${workspaces.key}:${JSON.stringify(initial)}`}
          preferences={preferences.profile}
          workspaces={workspaces}
          plans={plans.data ?? []}
          templates={templates.data}
          countries={countries.data ?? []}
          conflicts={(conflicts.data ?? []).map((card) => ({
            id: card.conflict.id,
            label: card.conflict.name,
          }))}
          hazards={(hazards.data ?? []).map((card) => ({ id: card.hazard, label: card.title }))}
          initial={initial}
          busy={generate.busy}
          error={generate.error === null ? null : describeError(generate.error)}
          onSubmit={(request) => void generate.run(request)}
        />
      )}
    </div>
  );
}
