import { render } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { vi } from 'vitest';
import { MapAreaResearchPanel } from '@/components/maps/MapAreaResearchPanel';
import { rectangleArea } from '@/lib/map/areaGeometry';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import type { ComponentProps } from 'react';

export const researchArea = rectangleArea({ west: 0, east: 1, south: 50, north: 51 });
export const otherResearchArea = rectangleArea({ west: 2, east: 3, south: 50, north: 51 });
export const consentLabel =
  'Allow research providers to receive this area, question and period for collection.';

export function areaPreview(input: ResearchPlanInput, supported = true) {
  return {
    ...input,
    subject: null,
    country_iso: null,
    area: { geometry: input.research_area!.geometry, sha256: 'a'.repeat(64) },
    map_origin: null,
    request_limit: 24,
    seconds_limit: 180,
    item_limit: 800,
    policy_version: 'fixture',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
    tasks: [
      {
        source_id: 'research-firms',
        source_name: 'NASA FIRMS',
        selected: true,
        supported,
        spatial_supported: supported,
        spatial_scope: 'Bounded public observations.',
        language: null,
        terms: [],
        provenance: 'original_terms',
        temporal_scope: 'Recent observations',
      },
      {
        source_id: 'research-news',
        source_name: 'News archive',
        selected: true,
        supported: true,
        spatial_supported: false,
        spatial_scope: 'No area-based collection support.',
        language: null,
        terms: [],
        provenance: 'original_terms',
        temporal_scope: 'Publication time',
      },
    ],
  };
}

function Location() {
  return <output aria-label="Current location">{useLocation().pathname}</output>;
}
export function mountAreaPanel(
  overrides: Partial<ComponentProps<typeof MapAreaResearchPanel>> = {},
) {
  const props = {
    area: researchArea,
    areaError: null,
    picking: false,
    onStopDrawing: vi.fn(),
    children: <button type="button">Draw boundary</button>,
    ...overrides,
  };
  const content = (next = props) => (
    <MemoryRouter>
      <MapAreaResearchPanel {...next} />
      <Location />
    </MemoryRouter>
  );
  const view = render(content());
  return {
    ...view,
    update: (changes: Partial<typeof props>) => view.rerender(content({ ...props, ...changes })),
    stop: props.onStopDrawing,
  };
}
