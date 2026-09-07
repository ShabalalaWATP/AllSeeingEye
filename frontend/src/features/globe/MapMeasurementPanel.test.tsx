import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { MapMeasurementPanel } from '@/components/maps/MapMeasurementPanel';
import { useMapMeasurement } from './useMapMeasurement';

const engine = { onClick: () => () => undefined };
function Panel() {
  const measurement = useMapMeasurement(engine, true);
  return <MapMeasurementPanel key={measurement.resetSequence} value={measurement} />;
}
it('supports typed area vertices, undo, clear and clearing draft coordinates on access changes', async () => {
  const user = userEvent.setup();
  render(<Panel />);
  const add = async (lon: string, lat: string) => {
    await user.clear(screen.getByLabelText('Longitude'));
    await user.type(screen.getByLabelText('Longitude'), lon);
    await user.clear(screen.getByLabelText('Latitude'));
    await user.type(screen.getByLabelText('Latitude'), lat);
    await user.click(screen.getByRole('button', { name: 'Add coordinate' }));
  };
  await add('0', '0');
  await add('1', '0');
  await add('1', '1');
  await user.selectOptions(screen.getByLabelText('Measurement type'), 'area');
  expect(screen.getByLabelText('Measurement result')).toHaveTextContent('km²');
  await user.click(screen.getByRole('button', { name: 'Undo point' }));
  expect(screen.getByLabelText('Measurement result')).toHaveTextContent('Add more');
  act(() => invalidateWorkspaceAccess());
  expect(screen.getByText('0/32 points')).toBeInTheDocument();
  expect(screen.getByLabelText('Longitude')).toHaveValue(null);
  await add('0', '0');
  await user.click(screen.getByRole('button', { name: 'Clear measure' }));
  expect(screen.getByText('0/32 points')).toBeInTheDocument();
});
