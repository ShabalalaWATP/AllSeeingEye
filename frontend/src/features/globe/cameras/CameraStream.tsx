import { useEffect, useRef, useState } from 'react';
import type { Camera } from '@/lib/api/cameras';
import { isCameraStreamUrl } from '@/lib/api/cameras';
import { usePageVisible } from '@/components/brand/useMotionPreferences';

/** The player exists only after an explicit request, and releases streams on close. */
export function CameraStream({ camera }: { camera: Camera }) {
  const [playing, setPlaying] = useState(false);
  const visible = usePageVisible();
  const safe = isCameraStreamUrl(camera.stream_url, camera.stream_type === 'iframe');
  if (!safe || !camera.stream_url) return null;
  return (
    <section className="space-y-2" aria-label="Camera video">
      <p>
        {camera.stream_type === 'mp4' ? 'Provider video clip' : 'Provider stream'} · Availability
        and delay vary.
      </p>
      <button
        type="button"
        className="min-h-11 rounded border border-line px-3 text-cyan"
        onClick={() => setPlaying((value) => !value)}
      >
        {playing ? 'Stop video' : 'Play video'}
      </button>
      {playing && !visible && <p role="status">Video paused while this tab is hidden.</p>}
      {playing && visible && (
        <Player
          key={`${camera.id}:${camera.stream_url}`}
          url={camera.stream_url}
          kind={camera.stream_type ?? 'mp4'}
          title={camera.title}
        />
      )}
    </section>
  );
}
function Player({
  url,
  kind,
  title,
}: {
  url: string;
  kind: NonNullable<Camera['stream_type']>;
  title: string;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const element = video.current;
    if (!element) return;
    let current = true;
    let dispose: () => void = () => undefined;
    if (kind === 'hls') {
      void import('hls.js')
        .then(({ default: Hls, FetchLoader }) => {
          if (!current) return;
          if (!Hls.isSupported()) {
            setError(true);
            return;
          }
          const hls = new Hls({
            loader: FetchLoader,
            maxBufferLength: 20,
            backBufferLength: 0,
            fetchSetup: (context, init: RequestInit) => {
              if (!isCameraStreamUrl(context.url)) throw Error('Unapproved stream destination');
              return new Request(context.url, {
                ...init,
                credentials: 'omit',
                redirect: 'error',
                referrerPolicy: 'no-referrer',
              });
            },
          });
          hls.on(Hls.Events.ERROR, (_event, data) => {
            if (data.fatal) {
              setError(true);
              hls.destroy();
            }
          });
          hls.loadSource(url);
          hls.attachMedia(element);
          dispose = () => hls.destroy();
        })
        .catch(() => {
          if (current) setError(true);
        });
    } else element.src = url;
    return () => {
      current = false;
      dispose();
      element.pause();
      element.removeAttribute('src');
      element.load();
    };
  }, [url, kind]);
  if (kind === 'iframe')
    return (
      <>
        <iframe
          title={`Camera stream: ${title}`}
          src={url}
          sandbox="allow-scripts allow-same-origin allow-presentation"
          allow="fullscreen; encrypted-media"
          referrerPolicy="strict-origin-when-cross-origin"
          className="aspect-video w-full border-0"
        />
        <p className="text-muted">
          If the provider blocks playback here, use its website link below.
        </p>
      </>
    );
  if (kind === 'mjpeg')
    return (
      <>
        {' '}
        <img
          src={url}
          alt={`Camera stream: ${title}`}
          referrerPolicy="no-referrer"
          className="w-full"
          onError={() => setError(true)}
        />
        {error && <p role="alert">Video unavailable. Try the provider website.</p>}
      </>
    );
  return (
    <>
      <video
        ref={video}
        controls
        autoPlay
        playsInline
        muted
        preload="metadata"
        crossOrigin="anonymous"
        className="w-full"
        aria-label={`Camera stream: ${title}`}
        onError={() => setError(true)}
      />
      {error && <p role="alert">Video unavailable in this browser. Try the provider website.</p>}
    </>
  );
}
