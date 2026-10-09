import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import type { Camera } from '@/lib/api/cameras';
import { isCameraStreamUrl } from '@/lib/api/cameras';
import { CameraStream } from './CameraStream';
import { useEmbedConsentStore } from '@/stores/embedConsent';
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
  useEmbedConsentStore.getState().resetSession();
  mock.supported = true;
  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype, 'load').mockImplementation(() => undefined);
});

it('restores saved camera consent after a document restart but still waits for Play', async () => {
  const selected = {
    ...camera,
    stream_type: 'iframe' as const,
    stream_url: 'https://www.youtube.com/embed/UemFRPrl1hk',
  };
  const view = render(<CameraStream camera={selected} />);
  await userEvent.click(screen.getByRole('checkbox', { name: /^Remember/ }));
  await userEvent.click(screen.getByRole('checkbox', { name: /^Also save/ }));
  await userEvent.click(screen.getByRole('button', { name: 'Load video from YouTube' }));
  expect(document.querySelector('iframe')).not.toBeNull();
  view.unmount();
  useEmbedConsentStore.getState().resetSession();
  render(<CameraStream camera={selected} />);
  expect(document.querySelector('iframe')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: 'Play video' }));
  expect(document.querySelector('iframe')).not.toBeNull();
});

it.each([
  ['youtube', 'YouTube', 'https://www.youtube.com/embed/UemFRPrl1hk'],
  ['ipcamlive', 'IPCamLive', 'https://ipcamlive.com/player/player.php?alias=publiccamera'],
] as const)(
  'remembering %s never bypasses Play for the next camera',
  async (provider, name, url) => {
    const selected = { ...camera, stream_type: 'iframe' as const, stream_url: url };
    const view = render(<CameraStream camera={selected} />);
    expect(document.querySelector('iframe')).toBeNull();
    expect(screen.getByRole('link', { name: `${name} privacy policy` })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('checkbox', { name: /^Remember/ }));
    await userEvent.click(screen.getByRole('button', { name: `Load video from ${name}` }));
    expect(document.querySelector('iframe')).not.toBeNull();
    view.rerender(<CameraStream camera={{ ...selected, id: 'next-camera' }} />);
    expect(document.querySelector('iframe')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Play video' }));
    expect(document.querySelector('iframe')).not.toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Stop video' }));
    expect(screen.getByRole('button', { name: `Forget ${name} choice` })).toBeInTheDocument();
    act(() => useEmbedConsentStore.getState().forget(provider));
    expect(screen.getByRole('button', { name: `Load video from ${name}` })).toBeInTheDocument();
  },
);

it('destroys HLS while hidden and resumes the chosen stream only when visible', async () => {
  render(<CameraStream camera={camera} />);
  fireEvent.click(screen.getByRole('button', { name: 'Play video' }));
  await waitFor(() => expect(mock.source).toHaveBeenCalledTimes(1));
  act(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(mock.destroy).toHaveBeenCalledTimes(1);
  expect(screen.queryByLabelText('Camera stream: Public webcam')).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('paused');
  act(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await waitFor(() => expect(mock.source).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getByRole('button', { name: 'Stop video' }));
  act(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  act(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  expect(mock.source).toHaveBeenCalledTimes(2);
});

it.each(['iframe', 'mjpeg', 'mp4'] as const)(
  'unmounts %s media while the tab is hidden',
  (kind) => {
    const view = render(
      <CameraStream
        camera={{
          ...camera,
          stream_type: kind,
          stream_url:
            kind === 'iframe'
              ? 'https://www.youtube.com/embed/UemFRPrl1hk'
              : (camera.stream_url ?? null),
        }}
      />,
    );
    fireEvent.click(
      screen.getByRole('button', {
        name: kind === 'iframe' ? 'Load video from YouTube' : 'Play video',
      }),
    );
    expect(view.container.querySelector('iframe,img,video')).not.toBeNull();
    act(() => {
      Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(view.container.querySelector('iframe,img,video')).toBeNull();
  },
);
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
  await user.click(screen.getByRole('button', { name: 'Load video from YouTube' }));
  expect(screen.getByTitle('Camera stream: Public webcam')).toHaveAttribute(
    'src',
    'https://www.youtube-nocookie.com/embed/UemFRPrl1hk',
  );
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
