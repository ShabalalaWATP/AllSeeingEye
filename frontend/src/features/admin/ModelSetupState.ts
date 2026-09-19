import { useState } from 'react';
import { ApiError, describeError } from '@/lib/api/errors';
import { createLlmProfile, updateLlmProfile, testLlmProfile } from '@/lib/api/llm';
import type { LlmProfile, LlmProfileInput } from '@/lib/api/llm';
import { useScopedRequest } from '@/lib/hooks/useScopedRequest';
import { OPENAI_BASE_URL, TEXT_ROLES } from './llmPresentation';
import { regionFromEndpoint } from './BedrockRegion';
import type { ModelSetupAudience, ModelSetupFields, ModelSetupProps } from './ModelSetupTypes';

export function useModelSetupState({ initial, onSaved, onApply, onClose }: ModelSetupProps) {
  const request = useScopedRequest();
  const ready =
    initial?.is_tested && initial.tested_revision === initial.revision && initial.tested_config_hash
      ? initial
      : null;
  const [step, setStep] = useState(ready ? 5 : 0);
  const [fields, setFields] = useState<ModelSetupFields>(() => ({
    name: initial?.name ?? '',
    provider:
      initial?.provider === 'bedrock'
        ? 'bedrock'
        : !initial || initial.base_url === OPENAI_BASE_URL
          ? 'openai'
          : 'custom',
    baseUrl: initial?.base_url ?? OPENAI_BASE_URL,
    region: initial?.provider === 'bedrock' ? regionFromEndpoint(initial.base_url) : '',
    apiKey: '',
    model: initial?.model ?? '',
    effort: initial?.reasoning_effort ?? '',
  }));
  const [draft, setDraft] = useState<LlmProfile | undefined>(initial);
  const [tested, setTested] = useState<LlmProfile | null>(ready);
  const [busy, setBusy] = useState<'save' | 'test' | 'apply' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testMs, setTestMs] = useState<number | null>(null);
  const [audience, setAudience] = useState<ModelSetupAudience>({ scope: 'global', targetIds: [] });
  const storedKey =
    !!draft &&
    draft.provider === (fields.provider === 'bedrock' ? 'bedrock' : 'openai_compatible') &&
    draft.base_url.replace(/\/$/, '') === fields.baseUrl.trim().replace(/\/$/, '');
  const change = (patch: Partial<ModelSetupFields>) => {
    setFields((current) => ({ ...current, ...patch }));
    setTested(null);
    setTestMs(null);
    setError(null);
  };
  const test = async () => {
    const signal = request();
    setBusy('save');
    setError(null);
    setTested(null);
    setTestMs(null);
    let saved = false;
    try {
      const input: LlmProfileInput = {
        name: fields.name.trim(),
        provider: fields.provider === 'bedrock' ? 'bedrock' : 'openai_compatible',
        base_url: fields.baseUrl.trim(),
        model: fields.model.trim(),
        roles: [...TEXT_ROLES],
        max_output_tokens: draft?.max_output_tokens ?? 16000,
        temperature:
          fields.provider === 'bedrock'
            ? Math.min(draft?.temperature ?? 0.2, 1)
            : (draft?.temperature ?? 0.2),
        reasoning_effort:
          fields.provider === 'bedrock' || fields.effort === '' ? null : fields.effort,
        enabled: false,
        ...(fields.apiKey.trim() ? { api_key: fields.apiKey.trim() } : {}),
      };
      const profile = draft
        ? await updateLlmProfile(draft.id, input, signal)
        : await createLlmProfile(input, signal);
      signal.throwIfAborted();
      setDraft(profile);
      onSaved(profile);
      saved = true;
      setFields((current) => ({ ...current, apiKey: '' }));
      setBusy('test');
      const result = await testLlmProfile(profile.id, signal);
      signal.throwIfAborted();
      if (!result.ok || result.revision !== profile.revision || !result.tested_config_hash)
        throw new ApiError(
          422,
          'connection_test_failed',
          result.error ?? 'The model did not pass the compatibility test.',
        );
      const proof = {
        ...profile,
        is_tested: true,
        tested_at: result.tested_at,
        tested_revision: result.revision,
        tested_config_hash: result.tested_config_hash,
      };
      setDraft(proof);
      setTested(proof);
      setTestMs(Math.round(result.latency_ms));
      onSaved(proof);
    } catch (failure) {
      if (!signal.aborted) {
        setError(
          `${saved ? 'The draft was saved, but the test failed.' : 'The connection could not be saved.'} ${describeError(failure)} Your active connections have not changed.`,
        );
        if (!saved && failure instanceof ApiError && failure.fieldError('name')) setStep(0);
      }
    } finally {
      if (!signal.aborted) setBusy(null);
    }
  };
  const apply = async () => {
    if (!tested) return;
    const signal = request();
    setBusy('apply');
    setError(null);
    try {
      await onApply(tested, audience);
      signal.throwIfAborted();
      onClose();
    } catch (failure) {
      if (!signal.aborted)
        setError(
          `The assignment could not be saved. ${describeError(failure)} Your tested connection is still available to retry.`,
        );
    } finally {
      if (!signal.aborted) setBusy(null);
    }
  };
  return {
    step,
    setStep,
    fields,
    change,
    draft,
    tested,
    testMs,
    storedKey,
    busy,
    error,
    audience,
    setAudience,
    test,
    apply,
  };
}

export type ModelSetupState = ReturnType<typeof useModelSetupState>;
