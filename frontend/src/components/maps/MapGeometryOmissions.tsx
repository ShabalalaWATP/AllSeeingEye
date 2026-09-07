import type { GeometryOmission } from './frozenEvidenceGeometry';

export function MapGeometryOmissions({ omissions }: { omissions: GeometryOmission[] }) {
  if (!omissions.length) return null;
  return (
    <details className="text-xs text-muted">
      <summary>{omissions.length} geometries omitted from the map</summary>
      <p className="mt-2">
        Original evidence is retained. Omission does not mean absence of activity.
      </p>
      <ul className="mt-2 space-y-1">
        {omissions.map((item, index) => (
          <li key={index}>
            {item.label}: {item.reason}
          </li>
        ))}
      </ul>
    </details>
  );
}
