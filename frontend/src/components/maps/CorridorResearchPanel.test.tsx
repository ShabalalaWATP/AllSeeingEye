import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { CorridorResearchPanel } from './CorridorResearchPanel';
import type { Position } from '@/lib/map/geoJsonTypes';

it('hands a preview boundary to research without generating a report automatically', () => {
  const research = vi.fn();
  render(
    <CorridorResearchPanel
      points={[
        [0, 51],
        [0.01, 51],
      ]}
      onResearchArea={research}
    />,
  );
  expect(research).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Preview corridor for research' }));
  expect(research).toHaveBeenCalledWith(expect.objectContaining({ type: 'FeatureCollection' }));
  expect(screen.getByText(/Review the polygon/)).toBeVisible();
});

it('shows a geometry error without handing invalid or absent boundaries to research', () => {
  const research = vi.fn();
  const { rerender } = render(<CorridorResearchPanel points={[]} onResearchArea={research} />);
  expect(screen.getByRole('button', { name: 'Preview corridor for research' })).toBeDisabled();
  rerender(
    <CorridorResearchPanel
      points={[
        [179.9, 0],
        [-179.9, 0],
      ]}
      onResearchArea={research}
    />,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Preview corridor for research' }));
  expect(screen.getByRole('alert')).toHaveTextContent('180°');
  expect(research).not.toHaveBeenCalled();
});

it('requires an explicit approximation preview and opt-in before using a long route', () => {
  const research = vi.fn();
  const points = Array.from({ length: 50 }, (_, index): Position => [index / 1000, 51]);
  const { rerender } = render(<CorridorResearchPanel points={points} onResearchArea={research} />);
  const preview = screen.getByRole('button', { name: 'Preview corridor for research' });
  expect(preview).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Prepare simplified route preview' }));
  expect(
    screen.getByRole('img', { name: 'Original and simplified route comparison' }),
  ).toBeVisible();
  expect(preview).toBeDisabled();
  fireEvent.click(
    screen.getByRole('checkbox', { name: 'Use this approximate path for the corridor' }),
  );
  expect(preview).toBeEnabled();
  fireEvent.click(preview);
  expect(research).toHaveBeenCalledOnce();
  rerender(
    <CorridorResearchPanel
      points={points.map(([lon, lat]) => [lon, lat + 0.001])}
      onResearchArea={research}
    />,
  );
  expect(preview).toBeDisabled();
  expect(
    screen.queryByRole('img', { name: 'Original and simplified route comparison' }),
  ).not.toBeInTheDocument();
});

it('rejects blank corridor widths and reports failures handed back by research', () => {
  const research = vi.fn(() => {
    // Exercise the external callback's non-Error failure boundary deliberately.
    // eslint-disable-next-line @typescript-eslint/only-throw-error
    throw 'Research unavailable';
  });
  render(
    <CorridorResearchPanel
      points={[
        [0, 51],
        [0.01, 51],
      ]}
      onResearchArea={research}
    />,
  );
  fireEvent.change(screen.getByLabelText('Distance on each side (km)'), { target: { value: '' } });
  fireEvent.click(screen.getByRole('button', { name: 'Preview corridor for research' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Enter the distance on each side');
  expect(research).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Distance on each side (km)'), { target: { value: '1' } });
  fireEvent.click(screen.getByRole('button', { name: 'Preview corridor for research' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Could not create the corridor');
});

it('reports a rejected approximation and invalidates prior opt-in when tolerance changes', () => {
  const points = Array.from({ length: 80 }, (_, index): Position => [
    index * 0.001,
    index % 2 ? 0.003 : 0,
  ]);
  render(<CorridorResearchPanel points={points} onResearchArea={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('Allowed route deviation (m)'), {
    target: { value: '50' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Prepare simplified route preview' }));
  expect(screen.getByRole('alert')).toHaveTextContent('can deviate by up to');
  expect(screen.getByRole('button', { name: 'Preview corridor for research' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Allowed route deviation (m)'), {
    target: { value: '5000' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Prepare simplified route preview' }));
  fireEvent.click(
    screen.getByRole('checkbox', { name: 'Use this approximate path for the corridor' }),
  );
  expect(screen.getByRole('button', { name: 'Preview corridor for research' })).toBeEnabled();
  fireEvent.change(screen.getByLabelText('Allowed route deviation (m)'), {
    target: { value: '1000' },
  });
  expect(screen.getByRole('button', { name: 'Preview corridor for research' })).toBeDisabled();
});
