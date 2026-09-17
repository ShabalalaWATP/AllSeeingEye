import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, expect, it } from 'vitest';
import { server } from '@/test/server';
import { apiError } from '@/test/handlers';
import { draft } from './llmTestFixtures';
import { mockModelSetupDialog, openWizard } from './ModelSetupTestSupport';

beforeEach(mockModelSetupDialog);

async function modelStep() {
  const view = await openWizard();
  await view.user.type(screen.getByLabelText('Connection name'), 'Research model');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  return view;
}

it('supports account search, a manual ID, and refreshing the account list without losing the selection', async () => {
  const view = await modelStep();
  await view.user.selectOptions(await screen.findByLabelText('Account model'), 'gpt-5.6-luna');
  await view.user.type(screen.getByLabelText('Search models'), 'manual');
  expect(screen.getByLabelText('Account model')).toHaveValue('gpt-5.6-luna');
  await view.user.click(screen.getByRole('button', { name: 'Enter model ID manually' }));
  await view.user.clear(screen.getByLabelText('Exact model ID'));
  await view.user.type(screen.getByLabelText('Exact model ID'), 'custom-model');
  await view.user.click(screen.getByRole('button', { name: 'Use account model list' }));
  expect(
    screen.getByRole('option', { name: 'custom-model (entered manually)' }),
  ).toBeInTheDocument();
  server.use(
    http.post('/api/admin/llm/models/discover', () =>
      HttpResponse.json({ models: ['custom-model', 'gpt-5.6-luna'] }),
    ),
  );
  await view.user.click(screen.getByRole('button', { name: 'Refresh models' }));
  await screen.findByRole('option', { name: 'custom-model' });
  expect(screen.getByLabelText('Account model')).toHaveValue('custom-model');
});

it('allows exact model entry when discovery fails without losing the chosen ID', async () => {
  const view = await openWizard();
  server.use(
    http.post('/api/admin/llm/models/discover', () =>
      apiError(422, 'discovery_unavailable', 'The catalogue is unavailable.'),
    ),
  );
  await view.user.type(screen.getByLabelText('Connection name'), 'Manual research');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  expect(await screen.findByText(/Model discovery is unavailable/)).toHaveTextContent(
    'Refresh the list or enter an exact model ID.',
  );
  await view.user.type(screen.getByLabelText('Exact model ID'), 'manual-alternative');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  expect(screen.getByLabelText('Reasoning level')).toHaveValue('');
});

it('sets up a custom provider without an API key when that endpoint needs none', async () => {
  const view = await openWizard();
  await view.user.type(screen.getByLabelText('Connection name'), 'Local research');
  await view.user.click(screen.getByText('Provider: OpenAI'));
  await view.user.selectOptions(screen.getByLabelText('Provider'), 'custom');
  await view.user.type(screen.getByLabelText('API endpoint'), 'http://localhost:11434/v1');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  expect(screen.getByLabelText('API key')).not.toBeRequired();
  server.use(http.post('/api/admin/llm/models/discover', () => HttpResponse.json({ models: [] })));
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.type(await screen.findByLabelText('Exact model ID'), 'local-model');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed/);
  expect(view.state.saves[0]).toMatchObject({
    base_url: 'http://localhost:11434/v1',
    model: 'local-model',
    reasoning_effort: null,
  });
  expect(view.state.saves[0]).not.toHaveProperty('api_key');
});

it('resumes and tests saved Bedrock settings using the stored regional key', async () => {
  const view = await openWizard(
    draft({
      provider: 'bedrock',
      base_url: 'https://bedrock-runtime.eu-west-2.amazonaws.com',
      model: 'openai.gpt-oss-120b-1:0',
      reasoning_effort: null,
    }),
  );
  expect(screen.getByLabelText('Provider')).toHaveValue('bedrock');
  await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  expect(screen.getByLabelText('Bedrock API key')).not.toBeRequired();
  for (let step = 0; step < 3; step++)
    await view.user.click(screen.getByRole('button', { name: 'Continue' }));
  await view.user.click(screen.getByRole('button', { name: 'Test connection' }));
  await screen.findByText(/Connection test passed/);
  expect(view.state.models).toBe(0);
  expect(view.state.saves[0]).not.toHaveProperty('api_key');
});

it('blocks a duplicate name before contacting the provider', async () => {
  const view = await openWizard();
  view.state.profiles.push(draft({ name: 'Reserved name' }));
  await view.user.type(screen.getByLabelText('Connection name'), 'Reserved name');
  expect(screen.getByRole('alert')).toHaveTextContent('This name is already used.');
  expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
  expect(view.state.models).toBe(0);
});
