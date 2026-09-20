import { useSyncExternalStore, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { useAuthStore } from '@/stores/auth';
import { useProfile } from '@/stores/profile';
import { subscribeWorkspaceAccess, workspaceRevision } from '@/lib/workspaceAccess';
import { describeError } from '@/lib/api/errors';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import type { Profile } from '@/lib/api/profile';
import { RESEARCH_DEPTHS } from '@/components/research/ResearchDepth';
import { ResearchProgress } from '@/components/research/ResearchProgress';
import { MapToolIntro } from './MapToolIntro';
import { SaveResearchArea } from './SaveResearchArea';
import { AreaResearchSources } from './AreaResearchSources';
import { AreaEvidencePreview } from './AreaEvidencePreview';
import { AREA_PERIODS, useAreaResearch } from './useAreaResearch';

interface Props {
  area: LocalCollection | null;
  areaError: string | null;
  picking: boolean;
  onStopDrawing: () => void;
  children: ReactNode;
  events?: readonly LiveEvent[];
  onHighlight?: (event: LiveEvent) => void;
  fullPage?: boolean;
  initialPreferences?: Profile | null;
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

function AreaResearchWorkspace({
  area,
  areaError,
  picking,
  onStopDrawing,
  children,
  events,
  onHighlight,
  fullPage,
  initialPreferences,
}: Props) {
  const preferences = useProfile();
  const profile = initialPreferences ?? preferences.profile;
  const research = useAreaResearch(area, areaError, profile);
  const navigate = useNavigate();
  const { action } = research;
  const canCheck = !!area && !areaError && !picking && !!profile && !research.busy && !action.busy;
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
        {area && !areaError && !picking && (
          <SaveResearchArea key={JSON.stringify(area)} area={area} />
        )}
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
        {research.interval && (
          <p className="map-tool-help">
            Fixed interval:{' '}
            {new Date(research.interval.since).toLocaleString('en-GB', { timeZone: 'UTC' })}
            {' to '}
            {new Date(research.interval.until).toLocaleString('en-GB', {
              timeZone: 'UTC',
            })}{' '}
            UTC.{' '}
            {research.fixedInterval && (
              <button
                type="button"
                className="map-tool-text-button"
                onClick={() => research.setDays(research.days)}
              >
                Use a fresh rolling period
              </button>
            )}
          </p>
        )}
        <label className="map-tool-field">
          Research depth
          <select
            className="map-tool-input"
            value={research.mode}
            onChange={(event) =>
              research.setMode(
                RESEARCH_DEPTHS.find((item) => item.value === event.target.value)?.value ?? 'quick',
              )
            }
          >
            {RESEARCH_DEPTHS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label} · {item.length}
              </option>
            ))}
          </select>
        </label>
      </fieldset>
      {area && !areaError && !picking && events && (
        <AreaEvidencePreview
          area={area}
          events={events}
          days={research.days}
          interval={research.interval}
          {...(onHighlight ? { onHighlight } : {})}
        />
      )}
      {!fullPage && (
        <button
          type="button"
          className="map-tool-secondary"
          disabled={!canCheck}
          onClick={() => {
            if (research.prepareHandoff()) void navigate('/research?map_draft=1');
          }}
        >
          Continue on research page
        </button>
      )}
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
        {preferences.loading && !profile && (
          <p role="status" className="map-tool-help">
            Loading your report preferences…
          </p>
        )}
        {preferences.error && !profile && (
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
      {research.sourcePlan && (
        <AreaResearchSources
          plan={research.sourcePlan}
          selectedIds={research.sourceIds}
          onSelection={research.setSourceIds}
          current={!!research.preview}
          disabled={action.busy || research.busy || picking}
        />
      )}
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
        Saved to your personal reports using the configured AI connection. Accepted jobs continue
        when you leave this tool. Your question and settings remain during this signed-in session;
        source checks and disclosure approval must be renewed after reopening. Reports include cited
        evidence and uncertainty; collection is not exhaustive.
      </p>
    </form>
  );
}
