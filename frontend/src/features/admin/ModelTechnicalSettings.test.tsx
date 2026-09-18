import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import type { LlmProfileInput } from '@/lib/api/llm';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { draft } from './llmTestFixtures';
import { installModelWorkspace, luna } from './modelWorkspaceTestFixtures';

async function openTechnicalSettings() {
  const view = renderApp('/admin/llm', 'admin');
  await view.user.click(
    await screen.findByRole('button', { name: 'Advanced limits and embedding connections' }),
  );
  return view;
}

it('edits an embedding connection using its stored key and keeps it outside the live model cards', async () => {
  const embedding = draft({
    id: '99999999-9999-4999-8999-999999999999',
    name: 'Search',
    model: 'text-embedding-3-small',
    roles: ['embeddings'],
    reasoning_effort: null,
  });
  const workspace = installModelWorkspace([luna, embedding]);
  const { user } = await openTechnicalSettings();
  await user.click(screen.getByRole('button', { name: 'Edit Search' }));
  const form = screen.getByRole('form', { name: 'Edit Search' });
  expect(within(form).getByLabelText('API key')).toHaveValue('');
  await user.clear(within(form).getByLabelText('Connection name'));
  await user.type(within(form).getByLabelText('Connection name'), 'Report search');
  await user.click(within(form).getByText('Advanced settings', { exact: true }));
  await user.clear(within(form).getByLabelText('Response budget (includes reasoning)'));
  await user.type(within(form).getByLabelText('Response budget (includes reasoning)'), '32000');
  await user.clear(within(form).getByLabelText('Temperature'));
  await user.type(within(form).getByLabelText('Temperature'), '0.4');
  await user.click(within(form).getByLabelText('Enable this embeddings connection when saved'));
  await user.click(within(form).getByRole('button', { name: 'Save draft' }));
  await screen.findByRole('button', { name: 'Edit Report search' });
  expect(workspace.state.saves).toHaveLength(1);
  expect(workspace.state.saves[0]).toMatchObject({
    name: 'Report search',
    roles: ['embeddings'],
    reasoning_effort: null,
    enabled: true,
    max_output_tokens: 32000,
    temperature: 0.4,
  });
  expect(workspace.state.saves[0]).not.toHaveProperty('api_key');
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(workspace.writes).toHaveLength(0);
});

it('retains an embedding key after a failed save, retries it, and clears a cancelled editor', async () => {
  installModelWorkspace();
  const writes: LlmProfileInput[] = [];
  server.use(
    http.post('/api/admin/llm/models/discover', () => HttpResponse.json({ models: [] })),
    http.post('/api/admin/llm/profiles', async ({ request }) => {
      const input = (await request.json()) as LlmProfileInput;
      writes.push(input);
      if (writes.length === 1) return apiError(409, 'conflict', 'Choose a different name.');
      return HttpResponse.json(
        draft({
          ...input,
          id: '77777777-7777-4777-8777-777777777777',
          roles: ['embeddings'],
          api_key_hint: 'test',
        }),
        { status: 201 },
      );
    }),
  );
  const { user } = await openTechnicalSettings();
  await user.click(screen.getByRole('button', { name: 'Add embedding connection' }));
  await user.type(screen.getByLabelText('API key'), 'synthetic-embedding-key');
  await user.type(screen.getByLabelText('Model ID'), 'text-embedding-3-small');
  await user.click(screen.getByRole('button', { name: 'Save draft' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Choose a different name.');
  expect(screen.getByLabelText('API key')).toHaveValue('synthetic-embedding-key');
  await user.clear(screen.getByLabelText('Connection name'));
  await user.type(screen.getByLabelText('Connection name'), 'Search retry');
  await user.click(screen.getByRole('button', { name: 'Save draft' }));
  await screen.findByRole('button', { name: 'Edit Search retry' });
  expect(writes).toHaveLength(2);
  expect(writes.every((input) => input.api_key === 'synthetic-embedding-key')).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Add embedding connection' }));
  expect(screen.getByLabelText('API key')).toHaveValue('');
  await user.type(screen.getByLabelText('API key'), 'cancelled-synthetic-key');
  await user.click(
    within(screen.getByRole('form', { name: 'New AI connection' })).getByRole('button', {
      name: 'Cancel',
    }),
  );
  await user.click(screen.getByRole('button', { name: 'Add embedding connection' }));
  expect(screen.getByLabelText('API key')).toHaveValue('');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
