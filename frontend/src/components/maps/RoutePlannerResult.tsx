import type { NavigationRoute } from '@/lib/api/navigation';

export function RoutePlannerResult({ route }: { route: NavigationRoute }) {
  const minutes = Math.ceil(route.duration_seconds / 60);
  const time =
    minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  return (
    <section className="map-tool-result route-result" aria-label="Calculated route">
      <h3 className="map-tool-section-title">Route estimate</h3>
      <div role="status" aria-label="Route estimate">
        <dl className="route-result-metrics">
          <div>
            <dt>Distance</dt>
            <dd>
              {route.distance_km.toFixed(1)} <small>km</small>
            </dd>
          </div>
          <div>
            <dt>Estimated time</dt>
            <dd>{time}</dd>
          </div>
        </dl>
      </div>
      <p className="map-tool-help">{route.limitations}</p>
      <details className="map-tool-disclosure route-directions">
        <summary>Directions ({route.steps.length})</summary>
        <ol>
          {route.steps.map((step, index) => (
            <li key={index}>
              <span className="route-direction-number" aria-hidden="true">
                {index + 1}
              </span>
              <div>
                {step.instruction}
                <span className="map-tool-help route-direction-distance">
                  {step.distance_km.toFixed(2)} km
                </span>
              </div>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}

export function RouteProviderDetails() {
  return (
    <details className="map-tool-disclosure route-provider-details">
      <summary>Routing data &amp; provider terms</summary>
      <p className="map-tool-help">
        Routing: FOSSGIS Valhalla. Data ©{' '}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          OpenStreetMap contributors
        </a>{' '}
        (
        <a
          href="https://opendatacommons.org/licenses/odbl/index.html"
          target="_blank"
          rel="noreferrer"
        >
          ODbL
        </a>
        ).{' '}
        <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">
          Fix the map
        </a>{' '}
        ·{' '}
        <a
          href="https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/"
          target="_blank"
          rel="noreferrer"
        >
          Provider terms
        </a>
      </p>
    </details>
  );
}
