import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { discardResearchInput, geolocateResearchInput } from '@/lib/api/researchGeolocation';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { photoAssessment, photoReceipt, photoWorkspaces } from '@/test/photoGeolocationFixture';

import { PhotoGeolocationPanel } from './PhotoGeolocationPanel';

const reports = vi.hoisted(() => ({
  run: vi.fn().mockResolvedValue(undefined),
  busy: false,
  error: null,
  clearError: vi.fn(),
  progress: { snapshot: null, active: false, cancel: vi.fn() },
}));
vi.mock('./useResearchRun', () => ({ useResearchRun: () => reports }));
vi.mock('@/lib/api/researchInputs', async (original) => ({
  ...(await original<typeof import('@/lib/api/researchInputs')>()),
  uploadResearchInput: vi.fn(),
}));
vi.mock('@/lib/api/researchGeolocation', async (original) => ({
  ...(await original<typeof import('@/lib/api/researchGeolocation')>()),
  geolocateResearchInput: vi.fn(),
  discardResearchInput: vi.fn(),
}));
const upload = vi.mocked(uploadResearchInput);
const analyse = vi.mocked(geolocateResearchInput);
const discard = vi.mocked(discardResearchInput);
const ids = Array.from({ length: 6 }, (_, index) => `10000000-0000-4000-8000-00000000001${index}`);
const choose = (count = 2) =>
  fireEvent.change(screen.getByLabelText(/^Photographs?$/), {
    target: {
      files: Array.from(
        { length: count },
        (_, index) => new File(['image'], `view-${index + 1}.jpg`),
      ),
    },
  });
async function ready(count = 2) {
  choose(count);
  await screen.findByText(`Photo ready: view-${count}.jpg`);
  await waitFor(() => expect(screen.getByRole('checkbox')).toBeEnabled());
}

describe('combined photo geolocation', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    upload.mockReset();
    analyse.mockReset();
    discard.mockReset();
    reports.run.mockClear();
    discard.mockResolvedValue();
    upload.mockImplementation((file) =>
      Promise.resolve(
        photoReceipt({
          id: ids[Number(/\d+/.exec(file.name)?.[0] ?? 1) - 1] ?? photoReceipt().id,
          filename: file.name,
        }),
      ),
    );
    analyse.mockResolvedValue(photoAssessment());
  });

  it('submits six labelled photos together with a single disclosure and question', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await ready(6);
    expect(screen.getAllByRole('img')).toHaveLength(6);
    expect(screen.getByText('Photo 6')).toBeVisible();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Analyse 6 photos together' }));
    await screen.findByText('Unverified location candidates');
    expect(analyse).toHaveBeenCalledTimes(1);
    expect(analyse).toHaveBeenCalledWith(
      ids[0],
      expect.objectContaining({
        additional_input_ids: ids.slice(1),
        consent_to_send_image: true,
        question: expect.stringContaining('whether they show the same location'),
      }),
      expect.any(AbortSignal),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Create saved report' }));
    expect(reports.run).toHaveBeenCalledWith(
      expect.objectContaining({
        research_input_id: photoAssessment().input.id,
        question: expect.stringContaining('compare the photos'),
      }),
    );
  });

  it('removing one photo clears findings and consent while retaining the other preview', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await ready();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Analyse 2 photos together' }));
    await screen.findByText('Unverified location candidates');
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo 1' }));
    expect(screen.queryByText('Unverified location candidates')).not.toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    await waitFor(() => expect(screen.getAllByRole('img')).toHaveLength(1));
    expect(discard).toHaveBeenCalledWith(ids[0], expect.any(AbortSignal));
    expect(screen.getByRole('button', { name: /^Analyse photos?$/ })).toBeDisabled();
  });

  it('rejects more than six or oversized photos before starting uploads', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose(7);
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose up to six');
    expect(upload).not.toHaveBeenCalled();
    const file = new File(['x'], 'large.jpg');
    Object.defineProperty(file, 'size', { value: 8 * 1024 * 1024 + 1 });
    fireEvent.change(screen.getByLabelText(/^Photographs?$/), { target: { files: [file] } });
    expect(await screen.findByRole('alert')).toHaveTextContent('no larger than 8 MiB');
    expect(upload).not.toHaveBeenCalled();
  });

  it('keeps a successful partial upload visible and releases it before replacing the set', async () => {
    upload.mockResolvedValueOnce(
      photoReceipt({ id: ids[0] ?? photoReceipt().id, filename: 'view-1.jpg' }),
    );
    upload.mockRejectedValueOnce(new ApiError(422, 'bad_image', 'Second photo cannot be decoded.'));
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('Second photo cannot be decoded');
    expect(screen.getAllByRole('img')).toHaveLength(1);
    await ready();
    expect(discard).toHaveBeenCalledWith(ids[0], expect.any(AbortSignal));
    expect(screen.getAllByRole('img')).toHaveLength(2);
  });

  it('stops the batch when the active account changes during upload', async () => {
    let finish: (value: ReturnType<typeof photoReceipt>) => void = () => undefined;
    upload.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose();
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
    act(() => useAuthStore.getState().setSession(tokenFor(adminUser)));
    await act(async () => {
      finish(photoReceipt());
      await Promise.resolve();
    });
    expect(upload).toHaveBeenCalledTimes(1);
    expect(upload.mock.calls[0]?.[1].aborted).toBe(true);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('renders cross-photo contradictions and separately labelled visual findings', async () => {
    analyse.mockResolvedValue(
      photoAssessment({
        photos: [
          {
            photo_id: 'photo-1',
            visual_clues: ['Brick clock tower.'],
            limitations: ['Sign unreadable.'],
          },
          {
            photo_id: 'photo-2',
            visual_clues: ['Concrete tower.'],
            limitations: ['Different view.'],
          },
        ],
        cross_photo_analysis: 'The tower materials differ, so a common location is uncertain.',
      }),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await ready();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Analyse 2 photos together' }));
    expect(await screen.findByText('How the photos fit together')).toBeVisible();
    fireEvent.click(screen.getByText('Photo 2: visual evidence'));
    expect(screen.getByText('Concrete tower.')).toBeVisible();
  });
});
