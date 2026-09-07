import { useState } from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { MapState } from '@/lib/api/mapViews';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import { MapOverlaySet } from './MapOverlaySet';
import { prepareEvidenceGeometry } from './frozenEvidenceGeometry';

function Harness() {
  const [overlays, setOverlays] = useState(savedMapFixture.revision.state.overlays);
  return (
    <>
      <MapOverlaySet
        overlays={overlays}
        onChange={setOverlays}
        preparedFirst={prepareEvidenceGeometry([], overlays).firstOverlay}
      />
      <output aria-label="Current overlays">{JSON.stringify(overlays)}</output>
    </>
  );
}

it.each([false, true])(
  'keeps later overlay edits when an earlier file read finishes (additional=%s)',
  async (additional) => {
    const readers: FileReader[] = [];
    const read = vi.spyOn(FileReader.prototype, 'readAsText').mockImplementation(function (
      this: FileReader,
    ) {
      readers.push(this);
    });
    try {
      render(<Harness />);
      const user = userEvent.setup();
      if (additional)
        await user.click(screen.getByRole('button', { name: 'Add another local overlay' }));
      const fields = additional
        ? within(screen.getByRole('group', { name: 'Additional local overlay' }))
        : screen;
      await user.click(fields.getByText('Private local GeoJSON overlay'));
      await user.type(fields.getByLabelText('Overlay source'), 'New import');
      fireEvent.change(fields.getByLabelText('Dataset date'), { target: { value: '2026-09-01' } });
      await user.type(fields.getByLabelText('Attribution / licence note'), 'Synthetic fixture');
      const text = JSON.stringify({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            properties: { label: 'New reference' },
            geometry: { type: 'Point', coordinates: [1, 2] },
          },
        ],
      });
      await user.upload(
        fields.getByLabelText('Local GeoJSON file'),
        new File([text], 'new.geojson', { type: 'application/geo+json' }),
      );
      expect(readers).toHaveLength(1);
      if (additional) await user.click(screen.getByRole('button', { name: 'Remove overlay 2' }));
      else await user.click(screen.getByLabelText('Show overlay 2: Second source'));
      const pending = readers[0]!;
      Object.defineProperty(pending, 'result', { value: text });
      act(() => {
        pending.onload?.call(pending, new ProgressEvent('load') as ProgressEvent<FileReader>);
      });
      const overlays = JSON.parse(
        screen.getByLabelText('Current overlays').textContent,
      ) as MapState['overlays'];
      expect(overlays).toHaveLength(2);
      if (additional) {
        expect(overlays.map((item) => item.source)).toEqual(['First source', 'New import']);
        expect(overlays[0]!.visible).toBe(false);
      } else {
        expect(overlays.map((item) => item.source)).toEqual(['New import', 'Second source']);
        expect(overlays[1]!.visible).toBe(false);
      }
    } finally {
      read.mockRestore();
    }
  },
);
