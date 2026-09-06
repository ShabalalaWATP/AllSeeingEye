import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { llmProfiles } from '@/test/fixtures';

import { LlmProfileForm } from './LlmProfileForm';

describe('connection draft form', () => {
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
    expect(screen.getByLabelText('Models returned by this account')).toBeVisible();
    await user.type(screen.getByLabelText('API key'), 'synthetic-new-key');
    expect(screen.queryByLabelText('Models returned by this account')).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText('API key'));
    expect(screen.getByLabelText('Models returned by this account')).toBeVisible();
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
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('max');
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
  it('offers the requested OpenAI preset with a masked key and saves an inactive draft', async () => {
    const submit = vi.fn();
    const user = userEvent.setup();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.openai.com/v1');
    expect(screen.getByLabelText('Model ID')).toHaveValue('gpt-5.6-luna');
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('max');
    expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password');
    await user.type(screen.getByLabelText('API key'), 'synthetic-test-key');
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        base_url: 'https://api.openai.com/v1',
        model: 'gpt-5.6-luna',
        reasoning_effort: 'max',
        max_output_tokens: 16000,
        api_key: 'synthetic-test-key',
        enabled: false,
        roles: ['direction', 'assessment', 'devil', 'translation'],
      }),
    );
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
