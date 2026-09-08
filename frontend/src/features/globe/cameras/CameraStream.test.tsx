import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import type { Camera } from '@/lib/api/cameras';
import { isCameraStreamUrl } from '@/lib/api/cameras';
import { CameraStream } from './CameraStream';
const mock = vi.hoisted(() => ({
  destroy: vi.fn(),
  source: vi.fn(),
  supported: true,
  errorHandler: null as null | ((_event: string, data: { fatal: boolean }) => void),
  config: null as null | { fetchSetup: (context: { url: string }, init: RequestInit) => Request },
}));
vi.mock('hls.js', () => ({
  FetchLoader: vi.fn(),
  default: class {
    static isSupported = () => mock.supported;
    static Events = { ERROR: 'error' };
    constructor(config: NonNullable<typeof mock.config>) {
      mock.config = config;
    }
    on(_event: string, handler: NonNullable<typeof mock.errorHandler>) {
      mock.errorHandler = handler;
    }
    loadSource(url: string) {
      mock.source(url);
    }
    attachMedia = vi.fn();
    destroy() {
      mock.destroy();
    }
  },
}));
const camera: Camera = {
  id: 'test',
  provider: 'test',
  title: 'Public webcam',
  latitude: 0,
  longitude: 0,
  snapshot_url: null,
  source_url: 'https://www.youtube.com/',
  attribution: 'Provider',
  captured_at: null,
  coordinate_precision: 'approximate',
  stream_type: 'hls',
  stream_url: 'https://pics.smartburgas.eu/m3u8/camera.m3u8',
};
beforeEach(() => {
  vi.clearAllMocks();
  mock.supported = true;
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, 'load').mockImplementation(() => undefined);
});
it('starts HLS only on request, restricts nested requests and destroys it on stop', async () => {
  const user = userEvent.setup();
  render(<CameraStream camera={camera} />);
  expect(mock.source).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Play video' }));
  await waitFor(() => expect(mock.source).toHaveBeenCalledWith(camera.stream_url));
  expect(() => mock.config!.fetchSetup({ url: 'http://127.0.0.1/private' }, {})).toThrow(
    'Unapproved',
  );
  expect(() =>
    mock.config!.fetchSetup({ url: 'https://s3-eu-west-1.amazonaws.com/other/stream.m3u8' }, {}),
  ).toThrow('Unapproved');
  const request = mock.config!.fetchSetup({ url: camera.stream_url! }, {});
  expect(request.credentials).toBe('omit');
  expect(request.redirect).toBe('error');
  await user.click(screen.getByRole('button', { name: 'Stop video' }));
  expect(mock.destroy).toHaveBeenCalled();
  expect(screen.queryByLabelText('Camera stream: Public webcam')).not.toBeInTheDocument();
});
it('shows an approved iframe only while enabled', async () => {
  const user = userEvent.setup();
  render(
    <CameraStream
      camera={{
        ...camera,
        stream_type: 'iframe',
        stream_url: 'https://www.youtube.com/embed/UemFRPrl1hk',
      }}
    />,
  );
  expect(screen.queryByTitle('Camera stream: Public webcam')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Play video' }));
  expect(screen.getByTitle('Camera stream: Public webcam')).toHaveAttribute(
    'sandbox',
    'allow-scripts allow-same-origin allow-presentation',
  );
  await user.click(screen.getByRole('button', { name: 'Stop video' }));
  expect(screen.queryByTitle('Camera stream: Public webcam')).not.toBeInTheDocument();
});
it('reports MJPEG errors and refuses unknown stream origins', async () => {
  const user = userEvent.setup();
  const view = render(<CameraStream camera={{ ...camera, stream_type: 'mjpeg' }} />);
  await user.click(screen.getByRole('button', { name: 'Play video' }));
  fireEvent.error(screen.getByRole('img'));
  expect(screen.getByRole('alert')).toHaveTextContent('Video unavailable');
  view.rerender(
    <CameraStream camera={{ ...camera, stream_url: 'https://evil.test/video.m3u8' }} />,
  );
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(isCameraStreamUrl('https://user:secret@pics.smartburgas.eu/video')).toBe(false);
  expect(isCameraStreamUrl('javascript:alert(1)', true)).toBe(false);
});

it('reports fatal stream failures and releases the failed HLS connection', async () => {
  render(<CameraStream camera={camera} />);
  fireEvent.click(screen.getByRole('button', { name: 'Play video' }));
  await waitFor(() => expect(mock.source).toHaveBeenCalled());
  act(() => mock.errorHandler?.('error', { fatal: false }));
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  act(() => mock.errorHandler?.('error', { fatal: true }));
  expect(screen.getByRole('alert')).toHaveTextContent('Video unavailable');
  expect(mock.destroy).toHaveBeenCalled();
});

it('explains unsupported HLS and labels MP4 as a clip', async () => {
  mock.supported = false;
  const view = render(<CameraStream camera={camera} />);
  fireEvent.click(screen.getByRole('button', { name: 'Play video' }));
  await screen.findByRole('alert');
  expect(mock.source).not.toHaveBeenCalled();
  view.unmount();
  render(<CameraStream camera={{ ...camera, stream_type: 'mp4' }} />);
  expect(screen.getByText(/Provider video clip/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Play video' }));
  const video = screen.getByLabelText('Camera stream: Public webcam');
  expect(video).toHaveAttribute('src', camera.stream_url);
  fireEvent.error(video);
  expect(screen.getByRole('alert')).toHaveTextContent('Video unavailable');
});
