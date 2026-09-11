import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { countries } from '@/test/fixtures';
import { CountryMultiSelect } from './CountryMultiSelect';

it('limits selection, makes removals reversible and resets explicitly to worldwide', async () => {
  const catalogue = ['GB', 'UA', 'FR', 'DE', 'IT', 'ES', 'NL', 'BE', 'PL'].map((code) => ({
    ...countries[0]!,
    iso2: code,
    name: `Country ${code}`,
  }));
  function Harness() {
    const [value, onChange] = useState(catalogue.slice(0, 8).map((country) => country.iso2));
    return <CountryMultiSelect countries={catalogue} value={value} onChange={onChange} />;
  }
  const user = userEvent.setup();
  render(<Harness />);
  await user.click(screen.getByText('Choose countries'));
  expect(screen.getByRole('checkbox', { name: /Country PL/ })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Remove Country GB' }));
  expect(screen.getByRole('checkbox', { name: /Country PL/ })).toBeEnabled();
  await user.click(screen.getByRole('checkbox', { name: /Country PL/ }));
  await user.click(screen.getByRole('button', { name: 'Use worldwide' }));
  expect(screen.getByText('Worldwide', { exact: true })).toBeVisible();
  expect(screen.getByRole('checkbox', { name: /Country PL/ })).not.toBeChecked();
});
