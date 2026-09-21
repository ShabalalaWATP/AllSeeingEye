import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';
import { server } from '@/test/server';
import { LlmProfileForm } from './LlmProfileForm';

it('keeps the embedding purpose when changing between supported providers', async () => {
  server.use(http.post('/api/admin/llm/models/discover', () => HttpResponse.json({ models: [] })));
  const submit = vi.fn();
  const user = userEvent.setup();
  render(
    <LlmProfileForm
      embeddingsOnly
      busy={false}
      error={null}
      onSubmit={submit}
      onCancel={vi.fn()}
    />,
  );
  await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
  await user.type(screen.getByLabelText('Base URL'), 'http://localhost:11434/v1');
  await user.type(screen.getByLabelText('Model ID'), 'embeddinggemma');
  await user.click(screen.getByText('Advanced settings'));
  expect(screen.getByLabelText('Use this connection for embeddings only')).toBeChecked();
  expect(screen.getByLabelText('Use this connection for embeddings only')).toBeDisabled();
  expect(screen.queryByRole('option', { name: 'Amazon Bedrock' })).not.toBeInTheDocument();
  await user.click(screen.getByLabelText('Enable this embeddings connection when saved'));
  await user.click(screen.getByRole('button', { name: 'Save draft' }));
  expect(submit).toHaveBeenLastCalledWith(
    expect.objectContaining({ roles: ['embeddings'], enabled: true, reasoning_effort: null }),
  );
  await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
  await user.type(screen.getByLabelText('API key'), 'synthetic-key');
  await user.type(screen.getByLabelText('Model ID'), 'text-embedding-3-small');
  await user.click(screen.getByRole('button', { name: 'Save draft' }));
  expect(submit).toHaveBeenLastCalledWith(
    expect.objectContaining({ roles: ['embeddings'], enabled: false }),
  );
});
