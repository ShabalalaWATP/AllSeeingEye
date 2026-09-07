import { EvidenceProjectDetails } from '@/components/maps/EvidenceProjectDetails';
import { Button } from '@/components/ui/Button';
import type { EvidenceItem } from '@/lib/api/reports';
import { mapEvidenceDateLabel, evidencePrecision } from './evidenceGeometry';
import type { MapState } from '@/lib/api/mapViews';
import { EvidenceObservationDetails } from './EvidenceObservationDetails';
const PAGE_SIZE = 20;
export function MapEvidenceList({
  filtered,
  current,
  setPage,
  chosen,
  select,
  onSelectEvidence,
  timeBasis,
}: {
  filtered: EvidenceItem[];
  timeBasis: MapState['time_basis'];
  current: number;
  setPage: (value: number) => void;
  chosen: EvidenceItem | undefined;
  select: (label: string) => void;
  onSelectEvidence?: ((label: string) => void) | undefined;
}) {
  return (
    <>
      {filtered.length === 0 ? (
        <p>No saved evidence matches these filters.</p>
      ) : (
        <ul aria-label="Map evidence" className="grid gap-2 sm:grid-cols-2">
          {filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE).map((item) => (
            <li key={item.label}>
              <button
                type="button"
                aria-pressed={chosen?.label === item.label}
                onClick={() => select(item.label)}
                className="min-h-11 w-full rounded border border-line p-3 text-left text-sm hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-ember"
              >
                <span className="font-medium">
                  {item.label}: {item.title}
                </span>
                <span className="mt-1 block text-xs text-muted">
                  {mapEvidenceDateLabel(item, timeBasis)} · {evidencePrecision(item)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {filtered.length > PAGE_SIZE && (
        <nav aria-label="Map evidence pages" className="flex items-center gap-3">
          <Button variant="secondary" disabled={current === 0} onClick={() => setPage(current - 1)}>
            Previous
          </Button>
          <span>
            {current + 1} / {Math.ceil(filtered.length / PAGE_SIZE)}
          </span>
          <Button
            variant="secondary"
            disabled={(current + 1) * PAGE_SIZE >= filtered.length}
            onClick={() => setPage(current + 1)}
          >
            Next
          </Button>
        </nav>
      )}
      {chosen && (
        <aside aria-label="Selected map evidence" className="space-y-2 border-t border-line pt-3">
          <h3 className="font-medium">
            {chosen.label}: {chosen.title}
          </h3>
          <p className="text-sm">{chosen.summary ?? 'No saved excerpt available.'}</p>
          <EvidenceProjectDetails item={chosen} />
          <EvidenceObservationDetails item={chosen} />
          <p className="text-xs text-muted">
            {chosen.source_name} · Grade {chosen.grade} · {evidencePrecision(chosen)}
          </p>
          {onSelectEvidence && (
            <Button variant="secondary" onClick={() => onSelectEvidence(chosen.label)}>
              Inspect citation {chosen.label}
            </Button>
          )}
        </aside>
      )}
    </>
  );
}
