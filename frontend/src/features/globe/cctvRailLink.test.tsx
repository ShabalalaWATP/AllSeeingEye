import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { isValidElement, useState } from 'react';
import { expect, it, vi } from 'vitest';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { mapReferencePanels } from './MapReferencePanels';

function Harness() {
  const [enabled, setEnabled] = useState(false);
  return (
    <GlobeControls layers={null}>
      <ControlPanel
        side="left"
        label="CCTV"
        icon="camera"
        on={enabled}
        onOpen={() => {
          if (!enabled) setEnabled(true);
        }}
      >
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => setEnabled(!enabled)}
        >
          Show public cameras
        </button>
      </ControlPanel>
    </GlobeControls>
  );
}

it('switches cameras on from the rail button and keeps the button lit while they are shown', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const rail = screen.getByRole('button', { name: 'CCTV' });
  expect(rail).not.toHaveAttribute('data-on');
  await user.click(rail);
  expect(screen.getByRole('switch', { name: 'Show public cameras' })).toBeChecked();
  expect(rail).toHaveAttribute('data-on', 'true');
  await user.click(rail);
  expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  expect(rail).toHaveAttribute('data-on', 'true');
  await user.click(rail);
  await user.click(screen.getByRole('switch', { name: 'Show public cameras' }));
  expect(rail).not.toHaveAttribute('data-on');
  await user.click(rail);
  await user.click(rail);
  expect(screen.getByRole('switch', { name: 'Show public cameras' })).toBeChecked();
});

it('wires the CCTV rail panel to the camera state', () => {
  const panel = (enabled: boolean, setEnabled: (value: boolean) => void) => {
    const panels = mapReferencePanels({
      precision: { filter: 'all' },
      cameras: { cameras: { enabled, setEnabled } },
    } as unknown as Parameters<typeof mapReferencePanels>[0]);
    const cctv = panels.find((element) => element.key === 'cctv');
    if (!isValidElement<{ on?: boolean; onOpen?: () => void }>(cctv)) throw new Error('missing');
    return cctv.props;
  };
  const off = vi.fn();
  const closed = panel(false, off);
  expect(closed.on).toBe(false);
  closed.onOpen?.();
  expect(off).toHaveBeenCalledWith(true);
  const on = vi.fn();
  const shown = panel(true, on);
  expect(shown.on).toBe(true);
  shown.onOpen?.();
  expect(on).not.toHaveBeenCalled();
});
