import type { ResearchPlan } from '@/lib/api/researchPlan';

const formatDate = (value: string) =>
  new Date(value).toLocaleString('en-GB', {
    timeZone: 'UTC',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

export function AreaResearchSources({
  plan,
  selectedIds,
  onSelection,
  current = true,
  disabled = false,
}: {
  plan: ResearchPlan;
  selectedIds?: string[] | null;
  onSelection?: (ids: string[] | null) => void;
  current?: boolean;
  disabled?: boolean;
}) {
  const sources = plan.tasks.filter(
    (task, index, all) => all.findIndex((item) => item.source_id === task.source_id) === index,
  );
  const supported = sources.filter((task) => task.supported && task.spatial_supported);
  const unavailable = sources.filter((task) => !task.supported || !task.spatial_supported);
  return (
    <section aria-label="Area source coverage" className="map-tool-section">
      <p className="map-tool-result" role="status">
        {supported.length} {supported.length === 1 ? 'source supports' : 'sources support'} this
        area search
      </p>
      <p className="map-tool-help">
        Capability check only. These sources have not been contacted and no results have been
        collected.
        {!current && ' Source selection changed. Check sources again before approving collection.'}
      </p>
      {onSelection && (
        <p className="map-tool-help">
          {
            supported.filter(
              (source) => selectedIds == null || selectedIds.includes(source.source_id),
            ).length
          }
          {' of '}
          {supported.length} supported sources selected. Collection budgets can limit which sources
          are reached; the saved report records actual requests, results and failures.
        </p>
      )}
      <p className="map-tool-help">
        {formatDate(plan.since)} to {formatDate(plan.until)} UTC. This interval stays fixed for the
        report.
      </p>
      <p className="map-tool-help">
        Up to {plan.request_limit} requests, {plan.seconds_limit} seconds of collection and{' '}
        {plan.item_limit} evidence items. Report analysis takes additional time. Provider responses
        and coverage are checked during collection.
      </p>
      {supported.length > 0 ? (
        <details className="map-tool-disclosure">
          <summary>Sources supporting this query ({supported.length})</summary>
          <ul className="map-tool-list">
            {supported.map((source) => (
              <li key={source.source_id} className="py-2">
                {onSelection ? (
                  <label className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      disabled={disabled}
                      checked={
                        selectedIds === null ||
                        selectedIds === undefined ||
                        selectedIds.includes(source.source_id)
                      }
                      onChange={(event) => {
                        const selected = new Set(
                          selectedIds ?? supported.map((item) => item.source_id),
                        );
                        if (event.target.checked) selected.add(source.source_id);
                        else selected.delete(source.source_id);
                        onSelection([...selected]);
                      }}
                    />
                    {source.source_name}
                  </label>
                ) : (
                  <p>{source.source_name}</p>
                )}
                <p className="map-tool-help">{source.spatial_scope}</p>
              </li>
            ))}
          </ul>
        </details>
      ) : (
        <p className="map-tool-notice" role="alert">
          No selected source supports this area and interval. Adjust the boundary or period and
          check again.
        </p>
      )}
      {onSelection && (
        <button
          type="button"
          className="map-tool-text-button"
          disabled={disabled || selectedIds === null}
          onClick={() => onSelection(null)}
        >
          Use all available sources
        </button>
      )}
      {unavailable.length > 0 && (
        <details className="map-tool-disclosure">
          <summary>Sources without area support ({unavailable.length})</summary>
          <ul className="map-tool-list">
            {unavailable.map((source) => (
              <li key={source.source_id} className="py-2">
                <p>{source.source_name}</p>
                <p className="map-tool-help">
                  {source.spatial_scope} {source.temporal_scope}
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="map-tool-help">
        A source catalogue entry or visible map layer is not necessarily searchable by area. Empty
        results do not establish that nothing happened. The report records collection gaps and
        source receipts.
      </p>
    </section>
  );
}
