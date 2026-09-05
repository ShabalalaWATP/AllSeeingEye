import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { llmProfiles } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function findRow(name: string): Promise<HTMLElement> {
  const table = await screen.findByRole('table', { name: 'Model profiles' });
  const cell = await within(table).findByText(name);
  const row = cell.closest('tr');
  if (row === null) throw new Error(`No row for ${name}`);
  return row;
}

describe('AdminLlmPage', () => {
  it('lists profiles with only a key hint and tests a connection', async () => {
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await findRow('Local Llama');
    expect(within(row).getByText('…1234')).toBeInTheDocument();
    expect(within(row).getByText('llama3.1:8b')).toBeInTheDocument();
    expect(within(row).getByText('enabled')).toBeInTheDocument();
    expect(within(row).getByText('assessment')).toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Test Local Llama' }));
    expect(await within(row).findByRole('status')).toHaveTextContent('OK, 812 ms, llama3.1:8b');
  });

  it('creates a profile from the form and sends the key once', async () => {
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post('/api/admin/llm/profiles', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            ...llmProfiles[0],
            id: '77777777-7777-4777-8777-777777777777',
            name: 'OpenAI',
            model: 'gpt-4.1-mini',
            base_url: 'https://api.openai.com/v1',
            api_key_hint: 'wxyz',
            roles: ['assessment', 'devil'],
          },
          { status: 201 },
        );
      }),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    await findRow('Local Llama');
    await user.click(screen.getByRole('button', { name: 'New profile' }));
    const form = screen.getByRole('form', { name: 'New model profile' });
    await user.type(within(form).getByLabelText('Name'), 'OpenAI');
    await user.type(within(form).getByLabelText('Model'), 'gpt-4.1-mini');
    await user.type(within(form).getByLabelText('Base URL'), 'https://api.openai.com/v1');
    await user.type(within(form).getByLabelText('API key'), 'sk-test-wxyz');
    await user.click(within(form).getByLabelText("Devil's advocate"));
    await user.click(within(form).getByRole('button', { name: 'Create profile' }));
    const row = await findRow('OpenAI');
    expect(within(row).getByText('…wxyz')).toBeInTheDocument();
    expect(body).toMatchObject({
      name: 'OpenAI',
      model: 'gpt-4.1-mini',
      base_url: 'https://api.openai.com/v1',
      api_key: 'sk-test-wxyz',
      roles: ['assessment', 'devil'],
      max_output_tokens: 4000,
      temperature: 0.2,
      enabled: true,
    });
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });

  it('edits a profile without resending the key and shows save failures', async () => {
    let body: Record<string, unknown> | null = null;
    server.use(
      http.put('/api/admin/llm/profiles/:id', async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        if (body.name === 'broken') return apiError(409, 'encryption_unavailable', 'No key.');
        return HttpResponse.json({ ...llmProfiles[0], name: String(body.name), enabled: false });
      }),
    );
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await findRow('Local Llama');
    await user.click(within(row).getByRole('button', { name: 'Edit Local Llama' }));
    const form = screen.getByRole('form', { name: 'Edit Local Llama' });
    expect(within(form).getByLabelText('Name')).toHaveValue('Local Llama');
    await user.clear(within(form).getByLabelText('Name'));
    await user.type(within(form).getByLabelText('Name'), 'broken');
    await user.click(within(form).getByRole('button', { name: 'Save changes' }));
    expect(await within(form).findByText('No key.')).toBeInTheDocument();

    await user.clear(within(form).getByLabelText('Name'));
    await user.type(within(form).getByLabelText('Name'), 'Local Llama v2');
    await user.click(within(form).getByLabelText('Enabled'));
    await user.click(within(form).getByRole('button', { name: 'Save changes' }));
    const updated = await findRow('Local Llama v2');
    expect(within(updated).getByText('disabled')).toBeInTheDocument();
    expect(body).not.toHaveProperty('api_key');
    expect(body).toMatchObject({ name: 'Local Llama v2', enabled: false });
  });

  it('deletes only after confirmation and cancels the form', async () => {
    const { user } = renderApp('/admin/llm', 'admin');
    const row = await findRow('Local Llama');
    await user.click(screen.getByRole('button', { name: 'New profile' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    await user.click(within(row).getByRole('button', { name: 'Delete Local Llama' }));
    await user.click(within(row).getByRole('button', { name: 'Confirm delete Local Llama' }));
    await waitFor(() => {
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
    });
    expect(screen.getByText(/No model profiles yet/)).toBeInTheDocument();
  });

  it('explains when the server cannot store keys', async () => {
    server.use(
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({ items: [], encryption_available: false }),
      ),
    );
    renderApp('/admin/llm', 'admin');
    expect(await screen.findByText('Keys cannot be stored')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'New profile' })).toBeDisabled();
  });
});
