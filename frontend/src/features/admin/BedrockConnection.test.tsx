import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';

import { bedrockEndpoint, regionFromEndpoint } from './BedrockRegion';
import { LlmProfileForm } from './LlmProfileForm';
import { draft, installConnections } from './llmTestFixtures';

const bedrock = () =>
  draft({
    provider: 'bedrock',
    name: 'Bedrock research',
    base_url: 'https://bedrock-runtime.eu-west-2.amazonaws.com',
    model: 'openai.gpt-oss-120b-1:0',
    reasoning_effort: null,
  });

describe('native Amazon Bedrock connection', () => {
  it('requires an explicit region, API key and model and saves a text-only native draft', async () => {
    installConnections();
    const user = userEvent.setup();
    const submit = vi.fn();
    render(<LlmProfileForm busy={false} error={null} onSubmit={submit} onCancel={vi.fn()} />);
    await user.type(screen.getByLabelText('API key'), 'synthetic-openai-key');
    await user.selectOptions(screen.getByLabelText('Provider'), 'bedrock');
    expect(screen.getByLabelText('AWS region')).toHaveValue('');
    expect(screen.getByLabelText('AWS region')).toBeRequired();
    expect(screen.getByLabelText('Base URL')).toHaveValue('');
    expect(screen.getByLabelText('Base URL')).toHaveAttribute('readonly');
    expect(screen.getByLabelText('Model or inference profile ID')).toHaveValue('');
    expect(screen.getByLabelText('Model or inference profile ID')).toHaveAttribute(
      'maxlength',
      '2048',
    );
    expect(screen.getByLabelText('Temperature')).toHaveAttribute('max', '1');
    expect(screen.getByLabelText('Bedrock API key')).toHaveValue('');
    expect(screen.getByLabelText('Bedrock API key')).toHaveAttribute('maxlength', '16384');
    expect(screen.getByLabelText('Bedrock API key')).toHaveAttribute('type', 'password');
    expect(screen.getByLabelText('Model or inference profile ID')).toHaveAttribute(
      'placeholder',
      'e.g. openai.gpt-oss-120b-1:0',
    );
    expect(
      screen.getByText(/Copy a Converse-compatible model or inference profile ID/),
    ).toBeVisible();
    expect(screen.queryByLabelText('Reasoning effort')).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText('Use this connection for embeddings only'),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText('AWS region'), 'us-east-1');
    expect(screen.getByLabelText('Base URL')).toHaveValue(
      'https://bedrock-runtime.us-east-1.amazonaws.com',
    );
    await user.type(screen.getByLabelText('Bedrock API key'), 'synthetic-bedrock-key');
    await user.type(
      screen.getByLabelText('Model or inference profile ID'),
      'openai.gpt-oss-120b-1:0',
    );
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'bedrock',
        name: 'Amazon Bedrock',
        base_url: 'https://bedrock-runtime.us-east-1.amazonaws.com',
        model: 'openai.gpt-oss-120b-1:0',
        api_key: 'synthetic-bedrock-key',
        reasoning_effort: null,
        enabled: false,
        roles: ['direction', 'assessment', 'devil', 'translation'],
      }),
    );
    await user.clear(screen.getByLabelText('AWS region'));
    await user.type(screen.getByLabelText('AWS region'), 'eu-west-2');
    expect(screen.getByLabelText('Bedrock API key')).toHaveValue('');
    await user.type(screen.getByLabelText('Bedrock API key'), 'synthetic-other-key');
    await user.selectOptions(screen.getByLabelText('Provider'), 'openai');
    expect(screen.getByLabelText('API key')).toHaveValue('');
    expect(screen.getByLabelText('Model ID')).toHaveValue('gpt-5.6-luna');
    expect(screen.getByLabelText('Reasoning effort')).toHaveValue('max');
  });

  it('recognises saved Bedrock drafts, preserves their key only at the same endpoint and never offers stale model discovery', async () => {
    const user = userEvent.setup();
    const submit = vi.fn();
    render(
      <LlmProfileForm
        initial={bedrock()}
        models={['old-model']}
        busy={false}
        error={null}
        onSubmit={submit}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('Provider')).toHaveValue('bedrock');
    expect(screen.getByLabelText('AWS region')).toHaveValue('eu-west-2');
    expect(screen.getByLabelText('Bedrock API key')).not.toBeRequired();
    expect(screen.queryByLabelText('Models returned by this account')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit.mock.calls[0]?.[0]).not.toHaveProperty('api_key');
    fireEvent.change(screen.getByLabelText('AWS region'), { target: { value: 'us-west-2' } });
    expect(screen.getByLabelText('Bedrock API key')).toBeRequired();
    await user.click(screen.getByRole('button', { name: 'Save draft' }));
    expect(submit).toHaveBeenCalledTimes(1);
  });

  it('requires a new key when changing protocol even if the regional endpoint stays the same', async () => {
    const user = userEvent.setup();
    render(
      <LlmProfileForm
        initial={{ ...bedrock(), provider: 'openai_compatible' }}
        busy={false}
        error={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await user.selectOptions(screen.getByLabelText('Provider'), 'bedrock');
    await user.type(screen.getByLabelText('AWS region'), 'eu-west-2');
    expect(screen.getByLabelText('Base URL')).toHaveValue(bedrock().base_url);
    expect(screen.getByLabelText('Bedrock API key')).toBeRequired();
    expect(screen.queryByText(/Leave blank to keep the stored key/)).not.toBeInTheDocument();
  });

  it('resets an embeddings configuration when selecting native Bedrock', async () => {
    const user = userEvent.setup();
    render(
      <LlmProfileForm
        initial={draft({ roles: ['embeddings'], enabled: true, temperature: 2 })}
        busy={false}
        error={null}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await user.selectOptions(screen.getByLabelText('Provider'), 'bedrock');
    expect(
      screen.queryByLabelText('Use this connection for embeddings only'),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText('Temperature')).toHaveValue(1);
    await user.selectOptions(screen.getByLabelText('Provider'), 'custom');
    expect(screen.getByLabelText('Use this connection for embeddings only')).not.toBeChecked();
  });

  it('supports explicit test and apply without making a catalogue request', async () => {
    const state = installConnections([bedrock()]);
    const { user } = renderApp('/admin/llm', 'admin');
    await user.click(await screen.findByText('Bedrock research'));
    const row = screen.getByText('Bedrock research').closest('li')!;
    expect(within(row).queryByRole('button', { name: /Load models/ })).not.toBeInTheDocument();
    expect(
      within(row).getByText(/Use a model or inference profile ID from the AWS console/),
    ).toBeVisible();
    await user.click(within(row).getByRole('button', { name: 'Test Bedrock research' }));
    await within(row).findByText(/Connection test passed/);
    await user.click(within(row).getByRole('button', { name: 'Review and apply' }));
    expect(screen.getByRole('group', { name: 'Confirm connection switch' })).toHaveTextContent(
      'https://bedrock-runtime.eu-west-2.amazonaws.com',
    );
    await user.click(screen.getByRole('button', { name: 'Confirm switch' }));
    await screen.findByText('Global connection switched to openai.gpt-oss-120b-1:0.');
    expect(state.tests).toBe(1);
    expect(state.models).toBe(0);
    expect(state.applies[0]?.profile_id).toBe(bedrock().id);
  });

  it('accepts only canonical regional endpoint construction', () => {
    expect(bedrockEndpoint('eu-west-2')).toBe('https://bedrock-runtime.eu-west-2.amazonaws.com');
    for (const value of ['', 'us-east-1/evil', 'us-east-1@evil.example', 'https://example.test'])
      expect(bedrockEndpoint(value)).toBe('');
    expect(regionFromEndpoint('https://bedrock-runtime.eu-west-2.amazonaws.com/')).toBe(
      'eu-west-2',
    );
    expect(regionFromEndpoint('https://example.test')).toBe('');
  });
});
