import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import {
  editablePresetDefinition,
  fetchResearchPresets,
  type PresetItem,
} from '@/lib/api/researchPresets';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { applySession } from '@/test/render';
import { PresetPicker } from './PresetPicker';

vi.mock('@/lib/api/researchPresets', () => ({
  editablePresetDefinition: vi.fn(),
  fetchResearchPresets: vi.fn(),
}));
const fetchPresets = vi.mocked(fetchResearchPresets);
const definition = vi.mocked(editablePresetDefinition);

const starter: PresetItem = {
  preset: {
    id: 'local-review',
    version: 1,
    title: 'Local review',
    purpose: 'Review local changes.',
    group: 'cross_cutting',
    reviewed_on: '2026-09-01',
    question: 'What changed?',
    requirements: [
      { id: 'q1', question: 'Review the evidence', required: true, priority: 1 },
      { id: 'q2', question: 'Consider context', required: false, priority: 2 },
    ],
    required_inputs: [],
    scope_note: 'Declared scope',
    suggested_languages: [],
    language_note: '',
    source_bundles: [],
    lens_choices: ['general'],
    default_lens: 'general',
    default_depth: 'detailed',
    keywords: [],
  },
  readiness: {
    policy_version: 'test',
    source_bundles: [],
    sources: [],
    gaps: [],
    languages: [],
    candidate_provider_ids: ['source-one'],
    source_selection_required: true,
    required_input_ids: [],
    note: 'Review before applying.',
  },
};
const catalogue = (items = [starter]) => ({
  schema_version: 1 as const,
  items,
  lens_choices: ['general' as const],
  lens_rule: 'Evidence rules stay unchanged.',
});
const response = () => ({
  definition: newBriefDraft(),
  readiness: starter.readiness,
  omitted_requirement_ids: [],
  note: 'Editable only.',
});

beforeEach(() => {
  applySession('user');
  fetchPresets.mockReset().mockResolvedValue(catalogue());
  definition.mockReset().mockResolvedValue(response());
});

function mount(onApply = vi.fn(() => true), draft = newBriefDraft()) {
  const view = render(
    <MemoryRouter>
      <PresetPicker draft={draft} onApply={onApply} />
    </MemoryRouter>,
  );
  return { ...view, onApply, user: userEvent.setup() };
}

it('retries a failed catalogue and clearly reports an empty result', async () => {
  fetchPresets.mockRejectedValueOnce(
    new ApiError(503, 'unavailable', 'Presets are temporarily unavailable.'),
  );
  fetchPresets.mockResolvedValueOnce(catalogue([]));
  const { user } = mount();
  await user.click(await screen.findByRole('button', { name: 'Retry presets' }));
  expect(await screen.findByText('No presets match this search.')).toBeVisible();
  expect(fetchPresets.mock.calls[0]![0].aborted).toBe(true);
  expect(screen.queryByRole('button', { name: 'Apply preset to draft' })).not.toBeInTheDocument();
});

it('requires a question and current candidate source before applying, and preserves rejected drafts', async () => {
  const { user, onApply } = mount(vi.fn(() => false));
  await user.click(await screen.findByRole('button', { name: 'Local review' }));
  await user.click(screen.getByLabelText(/Review the evidence/));
  await user.click(screen.getByLabelText(/Consider context/));
  expect(screen.getByText('Select at least one requirement.')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Apply preset to draft' })).toBeDisabled();
  await user.click(screen.getByLabelText(/Review the evidence/));
  expect(screen.getByText('Choose at least one current candidate source.')).toBeVisible();
  await user.click(screen.getByLabelText('source-one'));
  await user.click(screen.getByLabelText('source-one'));
  expect(screen.getByRole('button', { name: 'Apply preset to draft' })).toBeDisabled();
  await user.click(screen.getByLabelText('source-one'));
  await user.click(screen.getByRole('button', { name: 'Apply preset to draft' }));
  await waitFor(() => expect(onApply).toHaveBeenCalledOnce());
  expect(definition).toHaveBeenCalledWith(
    starter,
    {
      depth: 'detailed',
      lens: 'general',
      selectedRequirementIds: ['q1'],
      selectedSourceIds: ['source-one'],
    },
    expect.any(AbortSignal),
  );
  expect(screen.queryByText(/applied to the editable draft/)).not.toBeInTheDocument();
});

it('limits source choices to 64 while allowing an existing choice to be removed', async () => {
  fetchPresets.mockResolvedValueOnce(
    catalogue([
      {
        ...starter,
        readiness: {
          ...starter.readiness,
          candidate_provider_ids: Array.from({ length: 65 }, (_, index) => `source-${index}`),
        },
      },
    ]),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: 'Local review' }));
  for (let index = 0; index < 64; index++)
    fireEvent.click(screen.getByLabelText(`source-${index}`));
  expect(screen.getByLabelText('source-64')).toBeDisabled();
  expect(screen.getByLabelText('source-0')).toBeEnabled();
  fireEvent.click(screen.getByLabelText('source-0'));
  expect(screen.getByLabelText('source-64')).toBeEnabled();
});

it('ignores a definition that finishes after the picker unmounts', async () => {
  let finish!: (value: ReturnType<typeof response>) => void;
  definition.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { user, unmount, onApply } = mount();
  await user.click(await screen.findByRole('button', { name: 'Local review' }));
  await user.click(screen.getByLabelText('source-one'));
  await user.click(screen.getByRole('button', { name: 'Apply preset to draft' }));
  expect(screen.getByLabelText('Preset group')).toBeDisabled();
  const signal = definition.mock.calls[0]![2];
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    finish(response());
    await Promise.resolve();
  });
  expect(onApply).not.toHaveBeenCalled();
});

it('filters non-area presets from a pinned map and hides a selection excluded by a search', async () => {
  const area = {
    ...starter,
    preset: { ...starter.preset, id: 'area-custom', title: 'Area starter' },
  };
  fetchPresets.mockResolvedValueOnce(catalogue([starter, area]));
  const draft = newBriefDraft();
  draft.scope.map_view_id = '7152e032-1be9-4295-8a52-d7c63db09de4';
  const { user } = mount(undefined, draft);
  await user.click(await screen.findByRole('button', { name: 'Area starter' }));
  expect(screen.queryByRole('button', { name: 'Local review' })).not.toBeInTheDocument();
  await user.type(screen.getByLabelText('Search presets'), 'unmatched');
  expect(screen.getByText('No presets match this search.')).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Selected preset details' })).not.toBeInTheDocument();
});
