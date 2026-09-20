import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures.events';
import { researchArea } from '@/test/areaResearchPanel';
import { AreaEvidencePreview } from './AreaEvidencePreview';

const interval = { since: '2026-09-05T00:00:00Z', until: '2026-09-06T00:00:00Z' };
it('caps the expanded list at the newest twenty and shows translated titles without map actions', () => {
  const events = Array.from({ length: 21 }, (_, index) =>
    liveEvent({
      id: String(index),
      title: `Original ${index}`,
      title_en: index ? `Translated ${index}` : null,
      point: { lon: 0.5, lat: 50.5 },
      published_at: `2026-09-05T${String(index).padStart(2, '0')}:00:00Z`,
    }),
  );
  render(<AreaEvidencePreview area={researchArea} events={events} days={1} interval={interval} />);
  fireEvent.click(screen.getByText('Precisely inside (21)'));
  expect(screen.getByText('Showing the 20 newest records in this group.')).toBeVisible();
  expect(screen.getByText('Translated 20')).toBeVisible();
  expect(screen.queryByText('Original 0')).not.toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});

it('keeps approximate context separate and highlights its translated record only on request', () => {
  const exact = liveEvent({
    id: 'exact',
    title: 'Original exact',
    title_en: null,
    point: { lon: 0.5, lat: 50.5 },
  });
  const city = liveEvent({
    id: 'city',
    title: 'Original city',
    title_en: 'Translated city',
    point: { lon: 0.5, lat: 50.5 },
    geo_confidence: 'city',
  });
  const highlight = vi.fn();
  const { rerender } = render(
    <AreaEvidencePreview
      area={researchArea}
      events={[exact, city]}
      days={1}
      interval={interval}
      onHighlight={highlight}
    />,
  );
  fireEvent.click(screen.getByText('Approximate context (1)'));
  fireEvent.click(screen.getByRole('button', { name: 'Translated city' }));
  expect(highlight).toHaveBeenCalledWith(city);
  rerender(
    <AreaEvidencePreview area={researchArea} events={[exact]} days={1} interval={interval} />,
  );
  fireEvent.click(screen.getByText('Precisely inside (1)'));
  expect(within(screen.getByRole('region')).getByText('Original exact')).toBeVisible();
});
