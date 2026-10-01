import { screen, within } from '@testing-library/react';
import { http } from 'msw';
import { expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function saveSubscription(fields: Record<string, string>) {
  server.use(
    http.post('/api/schedules', () =>
      apiError(422, 'validation_error', 'The request is invalid.', fields),
    ),
  );
  const view = renderApp('/subscriptions', 'user');
  const form = within(await screen.findByRole('form', { name: 'New subscription' }));
  await view.user.type(form.getByLabelText('Subscription name'), 'Energy watch');
  await view.user.type(form.getByLabelText('Question'), 'What changed in energy markets?');
  await view.user.click(form.getByRole('button', { name: 'Create subscription' }));
  return { ...view, form };
}

it('places server reasons beside the subscription fields and focuses them from the summary', async () => {
  const { user, form } = await saveSubscription({
    name: 'A subscription with this name already exists.',
    question: 'Ask a narrower question.',
    hour_utc: 'Input should be less than 24.',
  });
  const summary = await form.findByRole('alert', { name: 'Check these fields and try again:' });
  expect(summary).toHaveFocus();
  const name = form.getByLabelText('Subscription name');
  expect(name).toHaveAttribute('aria-invalid', 'true');
  expect(name).toHaveAccessibleDescription('A subscription with this name already exists.');
  expect(name).toHaveValue('Energy watch');
  expect(form.getByLabelText('Question')).toHaveAccessibleDescription('Ask a narrower question.');
  expect(screen.queryByText('The request is invalid.')).not.toBeInTheDocument();

  await user.click(within(summary).getByRole('link', { name: /Question: Ask a narrower/ }));
  expect(form.getByLabelText('Question')).toHaveFocus();
  await user.click(within(summary).getByRole('link', { name: /When to run/ }));
  expect(document.getElementById('subscription-timing')).toContainElement(
    document.activeElement as HTMLElement,
  );
});

it('keeps unmatched schedule paths in the summary', async () => {
  const { form } = await saveSubscription({ 'unexpected.path': 'Not allowed.' });
  const summary = await form.findByRole('alert', { name: 'The request is invalid.' });
  expect(summary).toHaveTextContent('Unexpected path: Not allowed.');
});
