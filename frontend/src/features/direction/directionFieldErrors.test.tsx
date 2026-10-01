import { screen, within } from '@testing-library/react';
import { http } from 'msw';
import { expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const rejected = (fields: Record<string, string>) => () =>
  apiError(422, 'validation_error', 'The request is invalid.', fields);

it('places plan reasons beside the plan fields, including nested requirement paths', async () => {
  server.use(
    http.post(
      '/api/direction/plans',
      rejected({
        'pirs.0.text': 'Write the requirement as one question.',
        'pirs.0.sirs.1.keywords': 'Too many keywords.',
      }),
    ),
  );
  const { user } = renderApp('/direction', 'user');
  const form = within(await screen.findByRole('form', { name: 'New collection plan' }));
  await user.type(form.getByLabelText('Plan name'), 'Scoped');
  await user.type(form.getByLabelText('Priority intelligence requirement'), 'Q?');
  await user.type(form.getByLabelText('Specific requirements'), 'Anything');
  await user.click(form.getByRole('button', { name: 'Add plan' }));

  const summary = await form.findByRole('alert', { name: 'Check these fields and try again:' });
  expect(summary).toHaveFocus();
  const pir = form.getByLabelText('Priority intelligence requirement');
  expect(pir).toHaveAttribute('aria-invalid', 'true');
  expect(pir).toHaveAccessibleDescription(
    'The question the plan serves, as one sentence. Write the requirement as one question.',
  );
  expect(form.getByLabelText('Specific requirements')).toHaveAttribute('aria-invalid', 'true');
  await user.click(within(summary).getByRole('link', { name: /Specific requirements/ }));
  expect(form.getByLabelText('Specific requirements')).toHaveFocus();
  expect(pir).toHaveValue('Q?');
});

it('places area reasons beside the area fields', async () => {
  server.use(http.post('/api/direction/aois', rejected({ name: 'Name already used.' })));
  const { user } = renderApp('/direction', 'user');
  const form = within(await screen.findByRole('form', { name: 'New area of interest' }));
  await user.type(form.getByLabelText('Area name'), 'North');
  await user.type(form.getByLabelText('West, south, east, north'), '1, 2, 3, 4');
  await user.click(form.getByRole('button', { name: 'Add area' }));

  const summary = await form.findByRole('alert', { name: 'Check these fields and try again:' });
  const name = form.getByLabelText('Area name');
  expect(name).toHaveAttribute('aria-invalid', 'true');
  expect(name).toHaveAccessibleDescription('Name already used.');
  await user.click(within(summary).getByRole('link', { name: /Area name/ }));
  expect(name).toHaveFocus();
});
