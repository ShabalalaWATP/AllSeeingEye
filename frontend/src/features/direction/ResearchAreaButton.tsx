import { useState } from 'react';
import { useNavigate } from 'react-router';
import { prepareAreaResearchHandoff } from '@/lib/areaResearchDraft';
import type { AreaOfInterest } from '@/lib/api/direction';
import { rectangleArea } from '@/lib/map/areaGeometry';
import { parseLocalGeoJson } from '@/lib/map/localGeoJson';

/** Copy an authorised saved boundary into a personal research draft without provider calls. */
export function ResearchAreaButton({ area }: { area: AreaOfInterest }) {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  if (!area.research_area && !area.bbox) return null;
  return (
    <>
      <button
        type="button"
        className="mr-3 text-sm text-ember hover:underline"
        title="Prepare personal research using this saved boundary"
        onClick={() => {
          try {
            const [west, south, east, north] = area.bbox ?? [];
            const geometry = area.research_area
              ? parseLocalGeoJson(JSON.stringify(area.research_area.geometry)).canonical
              : west !== undefined &&
                  south !== undefined &&
                  east !== undefined &&
                  north !== undefined
                ? rectangleArea({ west, south, east, north })
                : null;
            if (!geometry) throw new Error('This area has no supported boundary.');
            prepareAreaResearchHandoff(geometry);
            void navigate('/research?map_draft=1');
          } catch (failure) {
            setError(failure instanceof Error ? failure.message : 'Unable to prepare this area.');
          }
        }}
      >
        Research area
      </button>
      {error && (
        <p role="alert" className="text-xs text-critical">
          {error}
        </p>
      )}
    </>
  );
}
