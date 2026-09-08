import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { LayerPanel } from './LayerPanel';

it('exposes effective subgroup state and routes settings to their controls', async () => {
  const toggleCategory = vi.fn();
  const toggleObservation = vi.fn();
  const toggleLite = vi.fn();
  const toggleGnss = vi.fn();
  const changeWindow = vi.fn();
  render(
    <LayerPanel
      counts={{ disaster: 1 }}
      hidden={['disaster']}
      stats={null}
      status="live"
      error={null}
      terminator={false}
      lite={false}
      interference={false}
      windowHours={null}
      onWindow={changeWindow}
      onToggle={toggleCategory}
      onToggleTerminator={vi.fn()}
      onToggleLite={toggleLite}
      onToggleInterference={toggleGnss}
      observations={{
        events: [
          liveEvent({ category: 'disaster', subtype: 'thermal_detection', source_id: 'firms' }),
        ],
        visibility: { aircraft: true, vessels: true, firms: true },
        onToggle: toggleObservation,
      }}
    />,
  );
  const user = userEvent.setup();
  const firms = screen.getByRole('switch', { name: 'FIRMS thermal detections' });
  expect(firms).not.toBeChecked();
  expect(screen.getByText(/1 loaded in this scope/)).toHaveTextContent('category hidden');
  await user.click(firms);
  expect(toggleCategory).toHaveBeenCalledExactlyOnceWith('disaster');
  expect(toggleObservation).not.toHaveBeenCalled();
  await user.click(screen.getByRole('switch', { name: 'Lite mode off' }));
  expect(toggleLite).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('switch', { name: 'GNSS interference off' }));
  expect(toggleGnss).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('radio', { name: '6 h' }));
  expect(changeWindow).toHaveBeenCalledExactlyOnceWith(6);
});
