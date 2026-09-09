import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { createRfDraft } from '@/lib/map/rfDraft';
import type { RfDraft } from '@/lib/map/rfDraft';
import { RfModelControls, rfEnvironmentValid } from './RfModelControls';
function Fixture() {
  const [draft, setDraft] = useState<RfDraft>(createRfDraft);
  return (
    <>
      <RfModelControls draft={draft} onChange={setDraft} />
      <output aria-label="Valid settings">{String(rfEnvironmentValid(draft))}</output>
    </>
  );
}
it('preserves environmental drafts across model changes and rejects blanks', () => {
  render(<Fixture />);
  fireEvent.change(screen.getByLabelText('Sampling radius (km)'), { target: { value: '' } });
  expect(screen.getByLabelText('Valid settings')).toHaveTextContent('false');
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'hf-skywave' } });
  expect(screen.getByText(/not an ionospheric forecast/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Minimum launch elevation (degrees)'), {
    target: { value: '85' },
  });
  expect(screen.getByLabelText('Valid settings')).toHaveTextContent('false');
  fireEvent.change(screen.getByLabelText('Propagation model'), { target: { value: 'terrain' } });
  expect(screen.getByLabelText('Sampling radius (km)')).toHaveValue(null);
});
it('keeps ground presets editable and labels their assumptions', () => {
  render(<Fixture />);
  fireEvent.change(screen.getByLabelText('Propagation model'), {
    target: { value: 'hf-groundwave' },
  });
  fireEvent.change(screen.getByLabelText('Ground conductivity shortcut'), {
    target: { value: '5' },
  });
  expect(screen.getByLabelText('Ground conductivity (S/m)')).toHaveValue(5);
  fireEvent.change(screen.getByLabelText('Ground conductivity (S/m)'), {
    target: { value: '0.02' },
  });
  expect(screen.getByLabelText('Ground conductivity shortcut')).toHaveValue('custom');
});
