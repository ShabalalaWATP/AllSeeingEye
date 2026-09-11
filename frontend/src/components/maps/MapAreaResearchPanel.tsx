import { useSyncExternalStore, type ReactNode } from 'react';
import { useAuthStore } from '@/stores/auth';
import { useProfile } from '@/stores/profile';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { describeError } from '@/lib/api/errors';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import { ResearchProgress } from '@/components/research/ResearchProgress';
import { MapToolIntro } from './MapToolIntro';
import { AreaResearchSources } from './AreaResearchSources';
import { AREA_PERIODS, useAreaResearch } from './useAreaResearch';

interface Props {
  area: LocalCollection | null;
  areaError: string | null;
  picking: boolean;
  onStopDrawing: () => void;
  children: ReactNode;
}

/** Remount private drafts when account or workspace permissions change. */
export function MapAreaResearchPanel(props: Props) {
  const user = useAuthStore((state) => state.user);
  const revision = useSyncExternalStore(subscribeWorkspaceAccess, workspaceRevision);
  return (
    <AreaResearchWorkspace
      key={`${user?.id}:${user?.role}:${user?.is_active}:${revision}`}
      {...props}
    />
  );
}

function AreaResearchWorkspace({ area, areaError, picking, onStopDrawing, children }: Props) {
  const preferences = useProfile();
  const research = useAreaResearch(area, areaError, preferences.profile);
  const { action } = research;
  const canCheck =
    !!area && !areaError && !picking && !!preferences.profile && !research.busy && !action.busy;
  return (
    <form
      aria-label="Research this area"
      className="map-tool-workspace"
      onSubmit={(event) => {
        event.preventDefault();
        if (picking) return;
        onStopDrawing();
        void research.generate();
      }}
    >
      <MapToolIntro
        title="Research area"
        description="Draw a boundary, ask a question and build a sourced AI report from public evidence in the area."
        status={
          action.busy
            ? 'Research in progress'
            : research.preview
              ? 'Sources checked'
              : 'Area research'
        }
        statusActive={!!research.preview || action.busy}
      />
      <fieldset disabled={action.busy} className="map-tool-section min-w-0">
        <legend className="map-tool-section-title mb-2">1 · Choose an area</legend>
        {children}
        {areaError && (
          <p className="map-tool-notice" role="alert">
            {areaError}
          </p>
        )}
      </fieldset>
      <fieldset disabled={action.busy} className="map-tool-section min-w-0">
        <legend className="map-tool-section-title mb-2">2 · Set the question</legend>
        <label className="map-tool-field">
          Question (optional)
          <textarea
            className="map-tool-input resize-y"
            rows={3}
            maxLength={1000}
            value={research.question}
            placeholder="What would you like to understand about this area?"
            onChange={(event) => research.setQuestion(event.target.value)}
          />
        </label>
        <p className="map-tool-help">
          Leave blank for an overview of relevant evidence, developments and gaps.
        </p>
        <label className="map-tool-field">
          Research period
          <select
            className="map-tool-input"
            value={research.days}
            onChange={(event) => {
              const period = AREA_PERIODS.find((item) => String(item.days) === event.target.value);
              if (period) research.setDays(period.days);
            }}
          >
            {AREA_PERIODS.map((period) => (
              <option key={period.days} value={period.days}>
                {period.label}
              </option>
            ))}
          </select>
        </label>
        <label className="map-tool-field">
          Research depth
          <select
            className="map-tool-input"
            value={research.mode}
            onChange={(event) =>
              research.setMode(event.target.value === 'quick' ? 'quick' : 'detailed')
            }
          >
            <option value="detailed">Detailed, broader collection</option>
            <option value="quick">Quick, smaller collection</option>
          </select>
        </label>
      </fieldset>
      <section className="map-tool-section">
        <h3 className="map-tool-section-title">3 · Check sources and research</h3>
        <p className="map-tool-help">
          Check all available research sources for area support, within the collection budget.
          Checking sources does not contact providers or call AI.
        </p>
        <button
          type="button"
          className="map-tool-secondary"
          disabled={!canCheck}
          onClick={() => void research.checkSources()}
        >
          {research.busy
            ? 'Checking sources…'
            : research.preview
              ? 'Refresh source check'
              : 'Check sources'}
        </button>
        {!area && !areaError && (
          <p className="map-tool-help">Complete a boundary to check source coverage.</p>
        )}
        {picking && <p className="map-tool-help">Finish drawing before checking sources.</p>}
        {preferences.loading && !preferences.profile && (
          <p role="status" className="map-tool-help">
            Loading your report preferences…
          </p>
        )}
        {preferences.error && !preferences.profile && (
          <div className="map-tool-notice" role="alert">
            <p>Report preferences could not be loaded.</p>
            <button
              type="button"
              className="map-tool-text-button"
              onClick={() => void preferences.reload()}
            >
              Retry preferences
            </button>
          </div>
        )}
        {research.error && (
          <p className="map-tool-notice" role="alert">
            {research.error}
          </p>
        )}
      </section>
      {research.preview && <AreaResearchSources plan={research.preview} />}
      <fieldset
        disabled={action.busy || !research.eligible || picking}
        className="map-tool-section min-w-0"
      >
        <label className="flex min-h-11 items-start gap-3 text-xs leading-relaxed">
          <input
            type="checkbox"
            className="mt-1 size-4 shrink-0 accent-ember"
            checked={research.consent}
            onChange={(event) => research.setConsent(event.target.checked)}
          />
          Allow research providers to receive this area, question and period for collection.
        </label>
        <button
          type="submit"
          className="map-tool-primary"
          disabled={!research.consent || !research.eligible || research.busy || action.busy}
        >
          {action.busy ? 'Generating report…' : 'Generate area report'}
        </button>
      </fieldset>
      {action.error && (
        <p className="map-tool-notice" role="alert">
          {describeError(action.error)}
        </p>
      )}
      <ResearchProgress
        snapshot={action.progress.snapshot}
        active={action.progress.active}
        onCancel={action.progress.cancel}
        onRetry={() => void action.retry()}
      />
      <p className="map-tool-help">
        Saved to your personal reports using the configured AI connection. Closing this tool or
        accepted jobs continue when you leave this tool. Reports include cited evidence and
        uncertainty; collection is not exhaustive.
      </p>
    </form>
  );
}
