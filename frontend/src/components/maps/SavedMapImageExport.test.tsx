import { useEffect } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { applySession } from '@/test/render';
import { report } from '@/test/fixtures';
import { savedMapFixture as saved } from '@/test/fixtures.savedMaps';
import { fetchMapView } from '@/lib/api/mapViews';
import { fetchReport } from '@/lib/api/reports';
import { fetchMapImagePackage, mapPngBase64 } from '@/lib/api/mapImageExport';
import { saveBinaryFile } from '@/lib/downloadBinary';
import { SavedMapImageExport } from './SavedMapImageExport';
const mocks = vi.hoisted(() => ({ capture: vi.fn(), props: vi.fn(), available: true }));
vi.mock('@/lib/api/mapViews', async (original) => ({
  ...(await original<object>()),
  fetchMapView: vi.fn(),
}));
vi.mock('@/lib/api/reports', async (original) => ({
  ...(await original<object>()),
  fetchReport: vi.fn(),
}));
vi.mock('@/lib/api/mapImageExport', () => ({
  fetchMapImagePackage: vi.fn(),
  mapPngBase64: vi.fn(),
}));
vi.mock('@/lib/downloadBinary', () => ({ saveBinaryFile: vi.fn() }));
vi.mock('./EvidenceMapCanvas', () => ({
  default: function MockCanvas(props: { onCaptureReady: (value: unknown) => void }) {
    mocks.props(props);
    const { onCaptureReady } = props;
    useEffect(() => {
      onCaptureReady(mocks.available ? mocks.capture : null);
      return () => onCaptureReady(null);
    }, [onCaptureReady]);
    return <div>Actual map renderer boundary</div>;
  },
}));
beforeEach(() => {
  vi.clearAllMocks();
  mocks.available = true;
  applySession('user');
  vi.mocked(fetchMapView).mockResolvedValue(saved);
  vi.mocked(fetchReport).mockResolvedValue(report);
  mocks.capture.mockResolvedValue(new Blob(['png'], { type: 'image/png' }));
  vi.mocked(mapPngBase64).mockResolvedValue('cG5n');
  vi.mocked(fetchMapImagePackage).mockResolvedValue(new Blob(['zip']));
});
async function open() {
  const user = userEvent.setup();
  render(<SavedMapImageExport saved={saved} />);
  await user.click(screen.getByRole('button', { name: 'Open saved image preview' }));
  await screen.findByText('Actual map renderer boundary');
  return user;
}
it('fetches the exact old revision and report, redacts annotations, then captures and exports', async () => {
  const user = await open();
  expect(fetchMapView).toHaveBeenCalledWith(
    saved.view.id,
    saved.revision.id,
    expect.any(AbortSignal),
  );
  expect(fetchReport).toHaveBeenCalledWith(saved.view.report_id, 1, expect.any(AbortSignal));
  expect(mocks.props).toHaveBeenLastCalledWith(
    expect.objectContaining({
      camera: saved.revision.state.camera,
      captureEnabled: true,
      overlays: [],
      aoi: null,
      measurement: null,
      focusRequest: null,
    }),
  );
  expect(screen.getByText(/Derived redacted view/)).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  await waitFor(() => expect(saveBinaryFile).toHaveBeenCalled());
  expect(fetchMapImagePackage).toHaveBeenCalledWith(
    saved.view.id,
    saved.revision.id,
    { png_base64: 'cG5n', include_annotations: false, use_basis: 'standard', permitted_use: '' },
    expect.any(AbortSignal),
  );
});
it('requires a declaration before including saved private annotations', async () => {
  const user = await open();
  await user.click(screen.getByRole('checkbox'));
  const download = screen.getByRole('button', { name: 'Download map image ZIP' });
  expect(download).toBeDisabled();
  await user.type(
    screen.getByLabelText('Permitted use declaration'),
    'Internal authorised analysis',
  );
  await user.click(download);
  await waitFor(() =>
    expect(fetchMapImagePackage).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.objectContaining({
        include_annotations: true,
        permitted_use: 'Internal authorised analysis',
      }),
      expect.anything(),
    ),
  );
});
it('cannot download without an available renderer', async () => {
  mocks.available = false;
  await open();
  expect(screen.getByRole('button', { name: 'Download map image ZIP' })).toBeDisabled();
  expect(fetchMapImagePackage).not.toHaveBeenCalled();
});
it('shows capture/readiness failures without creating a package', async () => {
  mocks.capture.mockRejectedValue(new Error('Tiles did not become ready.'));
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Tiles did not become ready.');
  expect(fetchMapImagePackage).not.toHaveBeenCalled();
});
it('clears preview and aborts pending delivery when authority changes', async () => {
  let resolve!: (blob: Blob) => void;
  vi.mocked(fetchMapImagePackage).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  await waitFor(() => expect(fetchMapImagePackage).toHaveBeenCalled());
  const signal = vi.mocked(fetchMapImagePackage).mock.calls[0]![3];
  act(() => applySession('admin'));
  expect(signal.aborted).toBe(true);
  expect(screen.queryByText('Actual map renderer boundary')).not.toBeInTheDocument();
  await act(async () => {
    resolve(new Blob(['zip']));
    await Promise.resolve();
  });
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('preserves satellite basemap and requires a reuse declaration', async () => {
  vi.mocked(fetchMapView).mockResolvedValue({
    ...saved,
    revision: { ...saved.revision, state: { ...saved.revision.state, basemap: 'satellite' } },
  });
  const user = await open();
  expect(mocks.props).toHaveBeenLastCalledWith(expect.objectContaining({ basemap: 'satellite' }));
  expect(screen.getByRole('button', { name: 'Download map image ZIP' })).toBeDisabled();
  await user.selectOptions(screen.getByLabelText('Basemap reuse basis'), 'licensed');
  await user.type(screen.getByLabelText('Permitted use declaration'), 'Licensed publication');
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  await waitFor(() =>
    expect(fetchMapImagePackage).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.objectContaining({ use_basis: 'licensed' }),
      expect.anything(),
    ),
  );
});
it('rejects mismatched fresh revisions and reports API errors', async () => {
  vi.mocked(fetchMapView).mockResolvedValue({
    ...saved,
    revision: { ...saved.revision, id: 'other' },
  });
  render(<SavedMapImageExport saved={saved} />);
  await userEvent.click(screen.getByRole('button', { name: 'Open saved image preview' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('different saved map revision');
  expect(fetchReport).not.toHaveBeenCalled();
});

it('renders fresh immutable state even when the supplied state differs', async () => {
  render(
    <SavedMapImageExport
      saved={{
        ...saved,
        revision: {
          ...saved.revision,
          state: {
            ...saved.revision.state,
            camera: { ...saved.revision.state.camera, longitude: 110 },
          },
        },
      }}
    />,
  );
  await userEvent.click(screen.getByRole('button', { name: 'Open saved image preview' }));
  await screen.findByText('Actual map renderer boundary');
  expect(mocks.props).toHaveBeenLastCalledWith(
    expect.objectContaining({ camera: saved.revision.state.camera }),
  );
});
it('reports final API rejection without saving a download', async () => {
  vi.mocked(fetchMapImagePackage).mockRejectedValue(new Error('Map access was revoked.'));
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Map access was revoked.');
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
it('cancels during PNG conversion when preview closes', async () => {
  let resolve!: (value: string) => void;
  vi.mocked(mapPngBase64).mockImplementation(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  const user = await open();
  await user.click(screen.getByRole('button', { name: 'Download map image ZIP' }));
  await waitFor(() => expect(mapPngBase64).toHaveBeenCalled());
  await user.click(screen.getByRole('button', { name: 'Close preview' }));
  await act(async () => {
    resolve('cG5n');
    await Promise.resolve();
  });
  expect(fetchMapImagePackage).not.toHaveBeenCalled();
  expect(saveBinaryFile).not.toHaveBeenCalled();
});
