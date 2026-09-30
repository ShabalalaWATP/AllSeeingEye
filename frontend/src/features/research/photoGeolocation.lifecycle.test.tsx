import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  discardResearchInput,
  geolocateResearchInput,
  type ResearchGeolocation,
} from '@/lib/api/researchGeolocation';
import { uploadResearchInput } from '@/lib/api/researchInputs';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import {
  photoAssessment,
  photoReceipt,
  photoTeamId,
  photoWorkspaces,
} from '@/test/photoGeolocationFixture';

import { PhotoGeolocationPanel } from './PhotoGeolocationPanel';

const reportAction = vi.hoisted(() => ({
  run: vi.fn(),
  busy: false,
  error: null,
  clearError: vi.fn(),
  progress: { snapshot: null, active: false, cancel: vi.fn() },
}));
vi.mock('./useResearchRun', () => ({ useResearchRun: () => reportAction }));
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

function choose(name = 'landmark.jpg') {
  fireEvent.change(screen.getByLabelText(/^Photographs?$/), {
    target: { files: [new File(['photo'], name, { type: 'image/jpeg' })] },
  });
}
async function ready() {
  choose();
  await screen.findByText('Photo ready: landmark.jpg');
  fireEvent.click(screen.getByRole('checkbox'));
}
async function begin() {
  await ready();
  fireEvent.click(screen.getByRole('button', { name: /^Analyse photos?$/ }));
}

describe('photo geolocation workspace', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    reportAction.run.mockReset();
    reportAction.run.mockResolvedValue(undefined);
    upload.mockReset();
    analyse.mockReset();
    discard.mockReset();
    discard.mockResolvedValue();
    upload.mockResolvedValue(photoReceipt());
    analyse.mockResolvedValue(photoAssessment());
  });
  afterEach(() => vi.useRealTimers());

  it('cancels analysis and discards a late provider result', async () => {
    let finish: (value: ResearchGeolocation) => void = () => undefined;
    analyse.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel analysis' }));
    expect(analyse.mock.calls[0]?.[2].aborted).toBe(true);
    await act(async () => {
      finish(photoAssessment());
      await Promise.resolve();
    });
    expect(screen.getByText(/Analysis cancelled/)).toBeVisible();
    expect(screen.queryByText('Unverified location candidates')).not.toBeInTheDocument();
  });

  it.each(['account', 'access', 'destination'] as const)(
    'removes private results and consent after a change to %s',
    async (change) => {
      render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
      await begin();
      await screen.findByText('Unverified location candidates');
      act(() => {
        if (change === 'account') useAuthStore.getState().setSession(tokenFor(adminUser));
        else if (change === 'access') invalidateWorkspaceAccess();
        else
          fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: photoTeamId } });
      });
      expect(screen.queryByText('Unverified location candidates')).not.toBeInTheDocument();
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
      expect(screen.getByRole('checkbox')).not.toBeChecked();
    },
  );

  it('expires findings with the original attachment and prevents report creation', async () => {
    vi.useFakeTimers();
    upload.mockResolvedValue(
      photoReceipt({ expires_at: new Date(Date.now() + 1000).toISOString() }),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose();
    await act(async () => {
      await Promise.resolve();
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /^Analyse photos?$/ }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByText('Unverified location candidates')).toBeVisible();
    act(() => {
      vi.advanceTimersByTime(1001);
    });
    expect(screen.queryByRole('button', { name: 'Create saved report' })).not.toBeInTheDocument();
    expect(screen.getByText(/This photo has expired/)).toBeVisible();
  });
});
