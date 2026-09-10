import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { RfPowerInput } from './RfPowerInput';
it('allows fractional watt editing and invalidates blank or zero power', async () => {
  function Fixture() {
    const [dbm, setDbm] = useState('30');
    return (
      <>
        <RfPowerInput dbm={dbm} onChange={setDbm} />
        <output aria-label="Canonical dBm">{dbm}</output>
      </>
    );
  }
  const user = userEvent.setup();
  render(<Fixture />);
  const input = screen.getByLabelText('Transmit power (watts)');
  await user.clear(input);
  await user.type(input, '0.5');
  expect(input).toHaveValue(0.5);
  expect(Number(screen.getByLabelText('Canonical dBm').textContent)).toBeCloseTo(26.9897, 3);
  await user.clear(input);
  await user.type(input, '0');
  expect(screen.getByLabelText('Canonical dBm')).toBeEmptyDOMElement();
});
