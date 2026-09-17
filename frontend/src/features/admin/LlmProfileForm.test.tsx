import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { llmProfiles } from '@/test/fixtures';

import { http, HttpResponse } from 'msw';
import { server } from '@/test/server';
beforeEach(() =>
  server.use(http.post('/api/admin/llm/models/discover', () => HttpResponse.json({ models: [] }))),
);
import { LlmProfileForm } from './LlmProfileForm';
import { draft } from './llmTestFixtures';

describe('connection draft form', () => {
  it('keeps the focused manual model input when delayed discovery returns account models', async () => {
    let release!: () => void;
    let started = false;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/admin/llm/models/discover', async () => {
        started = true;
        await pending;
        return HttpResponse.json({ models: ['embedding-alpha'] });
      }),
    );
    const user = userEvent.setup();
    const submit = vi.fn();
    render(
      <LlmProfileForm
        embeddingsOnly
        busy={false}
        error={null}
        onSubmit={submit}
        onCancel={vi.fn()}
      />,
    );
    await user.type(screen.getByLabelText('API key'), 'synthetic-key');
    const input = screen.getByLabelText('Model ID');
    await user.click(input);
    await waitFor(() => expect(started).toBe(true));
    expect(input).toHaveFocus();
    await act(() => {
      release();
      return pending;
    });
    await screen.findByText(/1 models returned by this account/);
    expect(screen.getByLabelText('Model ID')).toBe(input);
    expect(input).toHaveFocus();
    await user.type(input, 'embedding-alpha-custom');
    expect(input).toHaveValue('embedding-alpha-custom');
    await user.click(screen.getByRole('button', { name: 'Choose from account models' }));
    expect(screen.queryByLabelText('Model ID')).not.toBeInTheDocument();
    await user.selectOptions(
      screen.getByLabelText('Models returned by this account'),
      'embedding-alpha',
    );
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'embedding-alpha', roles: ['embeddings'] }),
    );
  });
  it('chooses an unused model-based name and resets reasoning when changing models', async () => {
    const user = userEvent.setup();
    const submit = vi.fn();
    render(
      <LlmProfileForm
        names={['first-model', 'first-model 2']}
        busy={false}
        error={null}
        onSubmit={submit}
        onCancel={vi.fn()}
      />,
    );
    await user.type(screen.getByLabelText('API key'), 'synthetic-key');
    await user.type(screen.getByLabelText('Model ID'), 'first-model');
    expect(screen.getByLabelText('Connection name')).toHaveValue('first-model 3');
    await user.selectOptions(screen.getByLabelText('Reasoning effort'), 'max');
    await user.clear(screen.getByLabelText('Model ID'));
    await user.type(screen.getByLabelText('Model ID'), 'second-model');
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('');
    await user.clear(screen.getByLabelText('Connection name'));
    await user.type(screen.getByLabelText('Connection name'), 'My connection');
    await user.type(screen.getByLabelText('Model ID'), '-latest');
    expect(screen.getByLabelText('Connection name')).toHaveValue('My connection');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'second-model-latest', reasoning_effort: null }),
    );
  });
  it('hides old account model choices after a credential or endpoint change', async () => {
    const user = userEvent.setup();
    render(
      <LlmProfileForm
        initial={llmProfiles[0]}
        models={['old-account-model']}
        busy={false}
        error={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'Choose from account models' })).toBeVisible();
    await user.type(screen.getByLabelText('API key'), 'synthetic-new-key');
    expect(screen.queryByLabelText('Models returned by this account')).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText('API key'));
    expect(screen.getByRole('button', { name: 'Choose from account models' })).toBeVisible();
    await user.type(screen.getByLabelText('Base URL'), '/different');
    expect(screen.queryByLabelText('Models returned by this account')).not.toBeInTheDocument();
  });
  it('distinguishes provider defaults from disabled reasoning and clears a key when changing destination', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    await user.type(screen.getByLabelText('API key'), 'synthetic-openai-key');
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    expect(screen.getByLabelText('API key')).toHaveValue('');
    await user.type(screen.getByLabelText('Base URL'), 'http://localhost:11434/v1');
    await user.type(screen.getByLabelText('Model ID'), 'local-model');
    await user.selectOptions(screen.getByLabelText('Reasoning effort'), 'none');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenLastCalledWith(expect.objectContaining({ reasoning_effort: 'none' }));
    await user.selectOptions(screen.getByLabelText('Reasoning effort'), '');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenLastCalledWith(expect.objectContaining({ reasoning_effort: null }));
    await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('');
  });

  it('preserves the separate advanced embeddings configuration with explicit enablement', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    await user.clear(screen.getByLabelText('Connection name'));
    await user.type(screen.getByLabelText('Connection name'), 'Local search');
    await user.type(screen.getByLabelText('Base URL'), 'http://localhost:11434/v1');
    await user.type(screen.getByLabelText('Model ID'), 'local-embedding-model');
    await user.click(screen.getByText('Advanced settings'));
    await user.clear(screen.getByLabelText('Response budget (includes reasoning)'));
    await user.type(screen.getByLabelText('Response budget (includes reasoning)'), '8000');
    await user.clear(screen.getByLabelText('Temperature'));
    await user.type(screen.getByLabelText('Temperature'), '0.5');
    await user.click(screen.getByLabelText('Use this connection for embeddings only'));
    await user.click(screen.getByLabelText('Enable this embeddings connection when saved'));
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Local search',
        enabled: true,
        roles: ['embeddings'],
        max_output_tokens: 8000,
        temperature: 0.5,
        reasoning_effort: null,
      }),
    );
  });
  it('uses the official endpoint and requires an explicit model with provider defaults', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.openai.com/v1');
    expect(screen.getByLabelText('Model ID')).toHaveValue('');
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Save draft' })).toBeDisabled();
    await user.type(screen.getByLabelText('Model ID'), 'gpt-5.6-luna');
    expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password');
    await user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        base_url: 'https://api.openai.com/v1',
        model: 'gpt-5.6-luna',
        reasoning_effort: null,
        max_output_tokens: 16000,
        api_key: 'synthetic-test-key',
        enabled: false,
        roles: ['direction', 'assessment', 'devil', 'translation'],
      }),
    );
  });

  it('preserves the response budget across provider changes and manual edits', async () => {
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={vi.fn()} onCancel={vi.fn()} />);
    await user.click(screen.getByText('Advanced settings'));
    const budget = screen.getByLabelText('Response budget (includes reasoning)');
    expect(budget).toHaveValue(16000);
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    expect(budget).toHaveValue(16000);
    await user.selectOptions(screen.getByLabelText('Provider'), 'bedrock');
    expect(budget).toHaveValue(16000);
    await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
    expect(budget).toHaveValue(16000);
    await user.clear(budget);
    await user.type(budget, '9000');
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
    expect(budget).toHaveValue(9000);
  });

  it('preserves a saved 16k budget while editing', async () => {
    const user = userEvent.setup();
    render(
      <LlmProfileForm
        initial={draft()}
        busy={false}
        error={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await user.click(screen.getByText('Advanced settings'));
    const budget = screen.getByLabelText('Response budget (includes reasoning)');
    expect(budget).toHaveValue(16000);
    await user.selectOptions(screen.getByLabelText('Reasoning effort'), 'low');
    await user.selectOptions(screen.getByLabelText('Reasoning effort'), 'max');
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
    expect(budget).toHaveValue(16000);
  });

  it('allows a custom endpoint and manual model ID without requiring a key', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    await user.type(screen.getByLabelText('Base URL'), 'http://localhost:11434/v1');
    await user.type(screen.getByLabelText('Model ID'), 'local-model');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'local-model', reasoning_effort: null }),
    );
    expect(submit.mock.calls[0]?.[0]).not.toHaveProperty('api_key');
  });

  it('keeps existing credentials write-only and offers account-discovered IDs', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(
      <LlmProfileForm
        initial={llmProfiles[0]}
        models={['local-model']}
        busy={false}
        error={null}
        onSubmit={submit}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('API key')).toHaveValue('');
    await user.click(screen.getByRole('button', { name: 'Choose from account models' }));
    await user.selectOptions(
      screen.getByLabelText('Models returned by this account'),
      'local-model',
    );
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit.mock.calls[0]?.[0]).not.toHaveProperty('api_key');
    expect(submit).toHaveBeenCalledWith(expect.objectContaining({ model: 'local-model' }));
  });

  it('keeps embeddings separate and disables all controls during saving', () => {
    const submit = vi.fn();
    const props = { busy: false, error: null, onSubmit: submit, onCancel: vi.fn() };
    const { rerender } = render(<LlmProfileForm {...props} />);
    fireEvent.click(screen.getByText('Advanced settings'));
    fireEvent.click(screen.getByLabelText('Use this connection for embeddings only'));
    expect(screen.queryByLabelText('Reasoning effort')).not.toBeInTheDocument();
    rerender(<LlmProfileForm {...props} busy />);
    expect(screen.getByLabelText('API key')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Save draft' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  });
});
