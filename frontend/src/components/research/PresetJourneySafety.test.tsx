import { act, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';

import * as presets from '@/lib/api/researchPresets';
import { newBriefDraft } from '@/lib/researchBriefDraft';

import { BriefEditor } from './BriefEditor';

const starter: presets.PresetItem = {
  preset: {
    id: 'port',
    version: 1,
    title: 'Port starter',
    purpose: 'Review port evidence.',
    group: 'cross_cutting',
    reviewed_on: '2026-09-14',
    question: 'What changed at the port?',
    requirements: [{ id: 'port.q1', question: 'Did traffic change?', required: true, priority: 1 }],
    required_inputs: [],
    scope_note: 'Select scope.',
    suggested_languages: ['en'],
    language_note: 'Query language only.',
    source_bundles: [],
    lens_choices: ['general'],
    default_lens: 'general',
    default_depth: 'quick',
    keywords: ['port'],
  },
  readiness: {
    policy_version: 'test-v1',
    source_bundles: [],
    sources: [],
    gaps: [],
    languages: [],
    candidate_provider_ids: [],
    source_selection_required: false,
    required_input_ids: [],
    note: 'Connectivity is unverified.',
  },
};

function setup() {
  vi.spyOn(presets, 'fetchResearchPresets').mockResolvedValue({
    schema_version: 1,
    items: [starter],
    lens_choices: ['general'],
    lens_rule: 'Relevance only.',
  });
  let finish!: (result: Awaited<ReturnType<typeof presets.editablePresetDefinition>>) => void;
  const definition = vi.spyOn(presets, 'editablePresetDefinition').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const view = render(
    <MemoryRouter>
      <BriefEditor
        initial={{ draft: newBriefDraft(), brief: null, copy: false, mapTitle: null }}
        onSaved={vi.fn()}
      />
    </MemoryRouter>,
  );
  const settle = async () => {
    await act(async () => {
      finish({
        definition: {
          ...newBriefDraft(),
          title: 'Port starter',
          question: {
            main: starter.preset.question,
            requirements: starter.preset.requirements,
            exclusions: [],
          },
        },
        readiness: starter.readiness,
        omitted_requirement_ids: [],
        note: 'Editable only.',
      });
      await Promise.resolve();
    });
  };
  return { ...view, definition, settle, user: userEvent.setup() };
}

it('preserves newer edits when a preset response arrives from an earlier stage', async () => {
  const { user, definition, settle } = setup();
  await user.click(screen.getByRole('button', { name: 'Browse presets' }));
  await user.click(await screen.findByRole('button', { name: 'Port starter' }));
  await user.click(screen.getByRole('button', { name: 'Apply preset to draft' }));
  await waitFor(() => expect(definition).toHaveBeenCalledOnce());
  expect(screen.getByLabelText('Preset depth')).toBeDisabled();
  expect(screen.getByLabelText('Search presets')).toBeDisabled();
  await user.click(screen.getByRole('button', { name: '2 Scope' }));
  await user.type(screen.getByLabelText('Research subject'), 'Keep this newer subject');
  await settle();
  expect(screen.getByLabelText('Research subject')).toHaveValue('Keep this newer subject');
  expect(screen.getByText(/The draft changed while the preset was loading/)).toBeVisible();
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  await user.click(screen.getByRole('button', { name: '1 Brief' }));
  expect(screen.getByLabelText('Main research question')).toHaveValue('');
  expect(screen.queryByText(/Port starter applied to the editable draft/)).not.toBeInTheDocument();
});

it('aborts the preset request when leaving the editor and ignores its late result', async () => {
  const { user, definition, settle, unmount } = setup();
  await user.click(screen.getByRole('button', { name: 'Browse presets' }));
  await user.click(await screen.findByRole('button', { name: 'Port starter' }));
  await user.click(screen.getByRole('button', { name: 'Apply preset to draft' }));
  await waitFor(() => expect(definition).toHaveBeenCalledOnce());
  const signal = definition.mock.calls[0]?.[2];
  unmount();
  expect(signal?.aborted).toBe(true);
  await settle();
  expect(screen.queryByText(/Port starter applied to the editable draft/)).not.toBeInTheDocument();
});
