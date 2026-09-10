import type { ResearchPlan } from '@/lib/api/researchPlan';

const formatDate = (value: string) =>
  new Date(value).toLocaleString('en-GB', {
    timeZone: 'UTC',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

export function AreaResearchSources({ plan }: { plan: ResearchPlan }) {
  const sources = plan.tasks.filter(
    (task, index, all) =>
      task.selected && all.findIndex((item) => item.source_id === task.source_id) === index,
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
          <summary>Sources included ({supported.length})</summary>
          <ul className="map-tool-list">
            {supported.map((source) => (
              <li key={source.source_id} className="py-2">
                <p>{source.source_name}</p>
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
