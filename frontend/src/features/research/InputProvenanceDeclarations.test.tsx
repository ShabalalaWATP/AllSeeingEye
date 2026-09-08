import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/errors';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import type { ResearchInputReceipt } from '@/lib/api/researchInputs';
import { fetchDeclarationTargets, declareInputProvenance } from '@/lib/api/inputDeclarations';
import { useAuthStore } from '@/stores/auth';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { plainUser, tokenFor } from '@/test/fixtures';
import { ResearchInput } from './ResearchInput';

vi.mock('@/lib/api/researchInputs', () => ({ uploadResearchInput: vi.fn() }));
vi.mock('@/lib/api/inputDeclarations', () => ({
  fetchDeclarationTargets: vi.fn(),
  declareInputProvenance: vi.fn(),
}));
const original = '\u0634\u0631\u06a9\u062a\u200c\u0627\u0644\u0641 1404-01-01';
const receipt = (): ResearchInputReceipt => ({
  id: '10000000-0000-4000-8000-000000000001',
  filename: 'notes.txt',
  media_type: 'text/plain',
  sha256: 'a'.repeat(64),
  imported_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 15 * 60_000).toISOString(),
  event_count: 1,
  extracted_characters: 30,
  preview: original,
  limitations: [],
  previews: [],
});
beforeEach(() => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  vi.mocked(uploadResearchInput).mockResolvedValue(receipt());
  vi.mocked(fetchDeclarationTargets).mockResolvedValue({
    input_id: receipt().id,
    sha256: receipt().sha256,
    expires_at: receipt().expires_at,
    targets: [
      {
        event_id: 'passage',
        content_hash: 'b'.repeat(64),
        title: original,
        summary: 'Original summary',
        language: 'fa',
        transformations: [],
        source_dates: [],
      },
    ],
  });
});
async function open() {
  const changed = vi.fn();
  render(<ResearchInput onChange={changed} />);
  const user = userEvent.setup();
  fireEvent.change(screen.getByLabelText('Document or media'), {
    target: { files: [new File(['original'], 'notes.txt')] },
  });
  await screen.findByText('Attached: notes.txt');
  await user.click(screen.getByText('Declare source language or calendar'));
  await user.click(screen.getByRole('button', { name: 'Load original passages' }));
  await user.click(await screen.findByRole('button', { name: 'Add passage declaration' }));
  await user.selectOptions(screen.getByLabelText('Declaration 1 passage'), 'passage');
  return { user, changed };
}
it('sends an exact original field and explicit calendar declaration, adopting only the new receipt', async () => {
  const updated = {
    ...receipt(),
    id: '10000000-0000-4000-8000-000000000002',
    parent_input_id: receipt().id,
  };
  vi.mocked(declareInputProvenance).mockResolvedValue(updated);
  const { user, changed } = await open();
  await user.click(screen.getByLabelText('Declaration 1: supply text transformation'));
  fireEvent.change(screen.getByLabelText('Declaration 1 transformed text'), {
    target: { value: 'Sherkat-e Alef 1404-01-01' },
  });
  fireEvent.change(screen.getByLabelText('Declaration 1 method'), {
    target: { value: 'Operator supplied rendering' },
  });
  fireEvent.change(screen.getByLabelText('Declaration 1 source script'), {
    target: { value: 'Arab' },
  });
  fireEvent.change(screen.getByLabelText('Declaration 1 target script'), {
    target: { value: 'Latn' },
  });
  await user.click(screen.getByLabelText('Declaration 1: declare a source date'));
  fireEvent.change(screen.getByLabelText('Declaration 1 raw source date'), {
    target: { value: '1404-01-01' },
  });
  await user.selectOptions(screen.getByLabelText('Declaration 1 calendar'), 'solar_hijri_icu33');
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  await waitFor(() => expect(changed).toHaveBeenLastCalledWith(updated.id));
  expect(vi.mocked(declareInputProvenance).mock.calls[0]?.[1]).toMatchObject({
    sha256: receipt().sha256,
    declarations: [
      {
        event_id: 'passage',
        content_hash: 'b'.repeat(64),
        transformations: [
          {
            original_text: original,
            transformed_text: 'Sherkat-e Alef 1404-01-01',
            kind: 'transliteration',
            source_language: 'fa',
            source_script: 'Arab',
            target_script: 'Latn',
          },
        ],
        source_dates: [
          {
            raw_text: '1404-01-01',
            calendar: 'solar_hijri_icu33',
            role: 'publication',
            field: 'title',
          },
        ],
      },
    ],
  });
  expect(screen.queryByLabelText('Declaration 1 transformed text')).not.toBeInTheDocument();
});
it('rejects dates absent from the selected source and removes private declaration drafts when access changes', async () => {
  const { user } = await open();
  await user.click(screen.getByLabelText('Declaration 1: declare a source date'));
  fireEvent.change(screen.getByLabelText('Declaration 1 raw source date'), {
    target: { value: '2026-09-08' },
  });
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  expect(
    await screen.findByText('The raw date must appear exactly in the selected original field.'),
  ).toBeVisible();
  expect(declareInputProvenance).not.toHaveBeenCalled();
  act(() => invalidateWorkspaceAccess());
  await waitFor(() => expect(screen.queryByDisplayValue('2026-09-08')).not.toBeInTheDocument());
  expect(screen.queryByText(original)).not.toBeInTheDocument();
});
it('cancels a pending declaration without adopting its late response', async () => {
  let resolve: (value: ResearchInputReceipt) => void = () => undefined;
  vi.mocked(declareInputProvenance).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const { user, changed } = await open();
  await user.click(screen.getByLabelText('Declaration 1: declare a source date'));
  fireEvent.change(screen.getByLabelText('Declaration 1 raw source date'), {
    target: { value: '1404-01-01' },
  });
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  await user.click(screen.getByRole('button', { name: 'Cancel declaration request' }));
  act(() => resolve({ ...receipt(), id: '10000000-0000-4000-8000-000000000003' }));
  expect(changed).toHaveBeenLastCalledWith(receipt().id);
  expect(vi.mocked(declareInputProvenance).mock.calls[0]?.[2].aborted).toBe(true);
});

it('keeps translation and transliteration for the same original passage in one bounded declaration', async () => {
  vi.mocked(declareInputProvenance).mockResolvedValue({
    ...receipt(),
    id: '10000000-0000-4000-8000-000000000002',
    parent_input_id: receipt().id,
  });
  const { user } = await open();
  for (const index of [1, 2]) {
    if (index === 2) {
      await user.click(screen.getByRole('button', { name: 'Add passage declaration' }));
      await user.selectOptions(screen.getByLabelText('Declaration 2 passage'), 'passage');
    }
    await user.click(screen.getByLabelText(`Declaration ${index}: supply text transformation`));
    fireEvent.change(screen.getByLabelText(`Declaration ${index} transformed text`), {
      target: { value: index === 1 ? 'Company A' : 'Sherkat-e Alef' },
    });
    fireEvent.change(screen.getByLabelText(`Declaration ${index} method`), {
      target: { value: 'Operator supplied' },
    });
  }
  await user.selectOptions(
    screen.getByLabelText('Declaration 1 transformation kind'),
    'translation',
  );
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  await waitFor(() => expect(declareInputProvenance).toHaveBeenCalled());
  const body = vi.mocked(declareInputProvenance).mock.calls[0]?.[1];
  expect(body?.declarations).toHaveLength(1);
  expect(body?.declarations[0]?.transformations).toMatchObject([
    { kind: 'translation', original_text: original },
    { kind: 'transliteration', original_text: original },
  ]);
});

it('rejects a derived receipt whose recorded parent differs from the selected original', async () => {
  vi.mocked(declareInputProvenance).mockResolvedValue({
    ...receipt(),
    id: '10000000-0000-4000-8000-000000000002',
    parent_input_id: '10000000-0000-4000-8000-000000000009',
  });
  const { user, changed } = await open();
  await user.click(screen.getByLabelText('Declaration 1: declare a source date'));
  fireEvent.change(screen.getByLabelText('Declaration 1 raw source date'), {
    target: { value: '1404-01-01' },
  });
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  expect(
    await screen.findByText(
      'The declared attachment response could not be verified. Import the file again.',
    ),
  ).toBeVisible();
  expect(changed).toHaveBeenLastCalledWith(receipt().id);
});
it('shows a derived receipt as inspect-only and permits loading its retained provenance', async () => {
  const derived = { ...receipt(), parent_input_id: '10000000-0000-4000-8000-000000000009' };
  vi.mocked(uploadResearchInput).mockResolvedValue(derived);
  render(<ResearchInput onChange={vi.fn()} />);
  const user = userEvent.setup();
  fireEvent.change(screen.getByLabelText('Document or media'), {
    target: { files: [new File(['original'], 'notes.txt')] },
  });
  await screen.findByText('Attached: notes.txt');
  await user.click(screen.getByText('Declare source language or calendar'));
  expect(screen.getByText(/available for inspection only/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Load original passages' }));
  await screen.findByRole('button', { name: 'Refresh original passages' });
  expect(screen.queryByRole('button', { name: 'Add passage declaration' })).not.toBeInTheDocument();
  expect(
    screen.queryByRole('button', { name: 'Save declarations for this research' }),
  ).not.toBeInTheDocument();
});

it('validates declaration content before saving and clears field-specific text when the original field changes', async () => {
  const { user } = await open();
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  expect(await screen.findByText(/at least one declaration for each passage/)).toBeVisible();
  await user.click(screen.getByLabelText('Declaration 1: supply text transformation'));
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  expect(await screen.findByText(/transformed text and a method/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Declaration 1 transformed text'), {
    target: { value: 'Draft rendering' },
  });
  await user.selectOptions(screen.getByLabelText('Declaration 1 original field'), 'summary');
  expect(screen.getByLabelText('Declaration 1 transformed text')).toHaveValue('');
  expect(screen.getByText('Original summary')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Remove declaration 1' }));
  expect(screen.queryByLabelText('Declaration 1 transformed text')).not.toBeInTheDocument();
  expect(declareInputProvenance).not.toHaveBeenCalled();
});
it('rejects excessive per-passage declarations before spending a private input slot', async () => {
  const { user } = await open();
  for (let index = 1; index <= 5; index++) {
    if (index > 1) {
      await user.click(screen.getByRole('button', { name: 'Add passage declaration' }));
      await user.selectOptions(screen.getByLabelText(`Declaration ${index} passage`), 'passage');
    }
    await user.click(screen.getByLabelText(`Declaration ${index}: declare a source date`));
    fireEvent.change(screen.getByLabelText(`Declaration ${index} raw source date`), {
      target: { value: '1404-01-01' },
    });
  }
  await user.click(screen.getByRole('button', { name: 'Save declarations for this research' }));
  expect(
    await screen.findByText(
      'Use up to four text transformations and four source dates per passage, including retained source metadata.',
    ),
  ).toBeVisible();
  expect(declareInputProvenance).not.toHaveBeenCalled();
});

it.each(['wrong-id', 'wrong-hash', 'expired'])(
  'rejects %s declaration targets before displaying private passages',
  async (failure) => {
    vi.mocked(fetchDeclarationTargets).mockResolvedValue({
      input_id: failure === 'wrong-id' ? '10000000-0000-4000-8000-000000000009' : receipt().id,
      sha256: failure === 'wrong-hash' ? 'c'.repeat(64) : receipt().sha256,
      expires_at: failure === 'expired' ? '2000-01-01T00:00:00Z' : receipt().expires_at,
      targets: [],
    });
    render(<ResearchInput onChange={vi.fn()} />);
    const user = userEvent.setup();
    fireEvent.change(screen.getByLabelText('Document or media'), {
      target: { files: [new File(['original'], 'notes.txt')] },
    });
    await screen.findByText('Attached: notes.txt');
    await user.click(screen.getByText('Declare source language or calendar'));
    await user.click(screen.getByRole('button', { name: 'Load original passages' }));
    expect(
      await screen.findByText(
        'The declaration targets no longer match this attachment. Import it again.',
      ),
    ).toBeVisible();
    expect(
      screen.queryByRole('button', { name: 'Add passage declaration' }),
    ).not.toBeInTheDocument();
    expect(declareInputProvenance).not.toHaveBeenCalled();
  },
);

it('allows a failed source inspection to be retried without replacing the original receipt', async () => {
  vi.mocked(fetchDeclarationTargets).mockRejectedValueOnce(
    new ApiError(503, 'unavailable', 'Inspection temporarily unavailable.'),
  );
  const changed = vi.fn();
  render(<ResearchInput onChange={changed} />);
  const user = userEvent.setup();
  fireEvent.change(screen.getByLabelText('Document or media'), {
    target: { files: [new File(['original'], 'notes.txt')] },
  });
  await screen.findByText('Attached: notes.txt');
  await user.click(screen.getByText('Declare source language or calendar'));
  await user.click(screen.getByRole('button', { name: 'Load original passages' }));
  expect(await screen.findByRole('alert')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Load original passages' }));
  expect(await screen.findByRole('button', { name: 'Add passage declaration' })).toBeEnabled();
  expect(changed).toHaveBeenLastCalledWith(receipt().id);
});
