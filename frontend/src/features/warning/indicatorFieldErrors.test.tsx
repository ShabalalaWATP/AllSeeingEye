import { screen, within } from '@testing-library/react';
import { http } from 'msw';
import { expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function submitRule(fields: Record<string, string>) {
  server.use(
    http.post('/api/warning/indicators', () =>
      apiError(422, 'validation_error', 'The request is invalid.', fields),
    ),
  );
  const view = renderApp('/warning', 'user');
  const form = within(await screen.findByRole('form', { name: 'New indicator' }));
  await view.user.type(form.getByLabelText('Indicator name'), 'Sumy strikes');
  await view.user.click(form.getByRole('button', { name: 'Add indicator' }));
  return { ...view, form };
}

it('marks the rejected name field and links the reason from a focused summary', async () => {
  const { user, form } = await submitRule({
    name: 'Choose a different name.',
    cooldown_minutes: 'Input should be greater than 0.',
  });
  const summary = await form.findByRole('alert', { name: 'Check these fields and try again:' });
  expect(summary).toHaveFocus();
  const name = form.getByLabelText('Indicator name');
  expect(name).toHaveAttribute('aria-invalid', 'true');
  expect(name).toHaveAccessibleDescription('Choose a different name.');
  expect(name).toHaveValue('Sumy strikes');
  expect(summary).toHaveTextContent('Cooldown minutes: Input should be greater than 0.');
  expect(screen.queryByText('The request is invalid.')).not.toBeInTheDocument();

  await user.click(within(summary).getByRole('link', { name: /Indicator name/ }));
  expect(name).toHaveFocus();
});

it('moves focus to the area controls for a rejected nation list', async () => {
  const { user, form } = await submitRule({ 'countries.0': 'Unknown country code.' });
  const summary = await form.findByRole('alert', { name: 'Check these fields and try again:' });
  await user.click(within(summary).getByRole('link', { name: /Watch location/ }));
  expect(form.getByRole('group', { name: 'Watch location' })).toContainElement(
    document.activeElement as HTMLElement,
  );
});

it('keeps the generic message when no reason matches a field on the form', async () => {
  const { form } = await submitRule({ severity_floor: 'Input should be less than 100.' });
  const summary = await form.findByRole('alert', { name: 'The request is invalid.' });
  expect(summary).toHaveTextContent('Severity floor: Input should be less than 100.');
  expect(form.getByLabelText('Indicator name')).not.toHaveAttribute('aria-invalid');
});
