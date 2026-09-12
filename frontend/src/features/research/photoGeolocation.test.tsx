import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
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
  derivedPhotoId,
  photoAssessment,
  photoId,
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

  it('requires explicit consent for this photo, shows a sanitised preview and validates candidate uncertainty', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    expect(screen.getByRole('button', { name: /^Analyse photos?$/ })).toBeDisabled();
    choose();
    const image = await screen.findByRole('img');
    expect(image).toHaveAttribute('src', 'data:image/png;base64,iVBORw0KGgo=');
    expect(analyse).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /^Analyse photos?$/ })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Context or location hints'), {
      target: { value: 'Possibly England' },
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /^Analyse photos?$/ }));
    await screen.findByText('Unverified location candidates');
    expect(analyse).toHaveBeenCalledWith(
      photoId,
      {
        question: 'Where might this photograph have been taken?',
        hints: 'Possibly England',
        team_id: null,
        consent_to_send_image: true,
      },
      expect.any(AbortSignal),
    );
    expect(screen.getByText('Candidate position, not a verified pin')).toBeVisible();
    expect(screen.getByText(/uncertainty radius 1 km/)).toBeVisible();
    fireEvent.click(screen.getByText('Analysis record'));
    expect(screen.getByText('returned-vision-model')).toBeVisible();
  });

  it('creates a media report from the derived findings, without image bytes or a claimed country', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: photoTeamId } });
    await waitFor(() => expect(screen.getByLabelText('Workspace')).toHaveValue(photoTeamId));
    fireEvent.change(screen.getByLabelText(/^Question about the photos?$/), {
      target: { value: 'Where is this tower?' },
    });
    await begin();
    fireEvent.click(await screen.findByRole('button', { name: 'Create saved report' }));
    expect(analyse.mock.calls[0]?.[1].team_id).toBe(photoTeamId);
    expect(reportAction.run).toHaveBeenCalledWith({
      template: 'ask',
      question: 'Where is this tower?',
      research_focus: 'media',
      research_input_id: derivedPhotoId,
      research_mode: 'quick',
      research_web_search: false,
      research_languages: ['en'],
      report_language: 'en',
      report_style: 'assessment',
      devils_advocacy: false,
      window_hours: 24,
      team_id: photoTeamId,
      disclose_area_to_provider: false,
    });
  });

  it('makes an unknown result useful without fabricating a candidate or accuracy score', async () => {
    analyse.mockResolvedValue(
      photoAssessment({
        status: 'unknown',
        candidates: [],
        summary: 'No distinctive landmark is visible.',
      }),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    expect(await screen.findByText('No location identified')).toBeVisible();
    expect(screen.getByText('How to verify')).toBeVisible();
    expect(screen.queryByText('Candidate position, not a verified pin')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create saved report' })).toBeEnabled();
  });

  it('shows a model capability failure and permits a retry with the same explicit disclosure', async () => {
    analyse.mockRejectedValueOnce(
      new ApiError(422, 'invalid_request', 'The configured model does not support images.'),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The configured model does not support images.',
    );
    fireEvent.click(screen.getByRole('button', { name: /^Analyse photos?$/ }));
    await screen.findByText('Unverified location candidates');
    expect(analyse).toHaveBeenCalledTimes(2);
  });

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

  it('refuses non-image attachments locally and clears previous consent on replacement', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose('notes.pdf');
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a PNG, JPEG or WebP');
    expect(upload).not.toHaveBeenCalled();
    await ready();
    upload.mockResolvedValue(photoReceipt({ id: derivedPhotoId, filename: 'replacement.png' }));
    choose('replacement.png');
    await screen.findByText('Photo ready: replacement.png');
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByRole('button', { name: /^Analyse photos?$/ })).toBeDisabled();
  });

  it('aborts in-flight model analysis when its panel unmounts', async () => {
    analyse.mockImplementation(() => new Promise(() => undefined));
    const view = render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    await waitFor(() => expect(analyse).toHaveBeenCalledTimes(1));
    view.unmount();
    expect(analyse.mock.calls[0]?.[2].aborted).toBe(true);
  });

  it('allows cancelling a slow upload and removing an extracted photo', async () => {
    upload.mockImplementationOnce(() => new Promise(() => undefined));
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel upload' }));
    expect(upload.mock.calls[0]?.[1].aborted).toBe(true);
    expect(screen.getByText('Photo upload cancelled.')).toBeVisible();
    await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Remove photo' }));
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(discard).toHaveBeenCalledWith(photoId, expect.any(AbortSignal));
  });

  it('reports a decoding error and refuses analysis when no preview was extracted', async () => {
    upload.mockRejectedValueOnce(
      new ApiError(422, 'invalid_request', 'The photo cannot be decoded.'),
    );
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    choose();
    expect(await screen.findByRole('alert')).toHaveTextContent('The photo cannot be decoded.');
    upload.mockResolvedValue(photoReceipt({ previews: [] }));
    await ready();
    expect(screen.getByRole('button', { name: /^Analyse photos?$/ })).toBeDisabled();
    expect(analyse).not.toHaveBeenCalled();
  });

  it('does not save a derived analysis after its own receipt has expired', async () => {
    vi.useFakeTimers();
    analyse.mockResolvedValue(
      photoAssessment({
        input: photoReceipt({
          id: derivedPhotoId,
          expires_at: new Date(Date.now() + 1000).toISOString(),
        }),
      }),
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
    act(() => {
      vi.advanceTimersByTime(1001);
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create saved report' }));
    expect(screen.getByRole('alert')).toHaveTextContent('The analysis has expired.');
    expect(reportAction.run).not.toHaveBeenCalled();
  });

  it('renders sparse regional hypotheses safely and saves the default question', async () => {
    const result = photoAssessment();
    result.visual_clues = [];
    result.candidates[0] = {
      label: '<script>Regional possibility</script>',
      country_iso: null,
      precision: 'region',
      supporting_clues: ['The landscape may be consistent.'],
      contradictions: [],
      coordinates: null,
    };
    analyse.mockResolvedValue(result);
    const view = render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    expect(await screen.findByText('<script>Regional possibility</script>')).toBeVisible();
    expect(view.container.querySelector('script')).toBeNull();
    expect(screen.queryByText('Visible clues')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Create saved report' }));
    expect(reportAction.run).toHaveBeenCalledWith(
      expect.objectContaining({
        question: expect.stringContaining('Assess the unverified candidates'),
      }),
    );
  });

  it('cleans up original and derived receipts before an invalid-file retry or workspace switch', async () => {
    render(<PhotoGeolocationPanel workspaces={photoWorkspaces()} />);
    await begin();
    await screen.findByText('Unverified location candidates');
    choose('not-a-photo.pdf');
    await waitFor(() => expect(discard).toHaveBeenCalledWith(photoId, expect.any(AbortSignal)));
    await ready();
    fireEvent.click(screen.getByRole('button', { name: /^Analyse photos?$/ }));
    await screen.findByText('Unverified location candidates');
    fireEvent.change(screen.getByLabelText('Workspace'), { target: { value: photoTeamId } });
    await waitFor(() => expect(screen.getByLabelText('Workspace')).toHaveValue(photoTeamId));
    expect(discard).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
});
