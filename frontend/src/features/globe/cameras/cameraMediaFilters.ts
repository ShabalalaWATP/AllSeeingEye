import { isCameraImageUrl, isCameraStreamUrl, type Camera } from '@/lib/api/cameras';

export type CameraMediaKind = 'all' | 'streams' | 'clips' | 'snapshots' | 'links';
export const CAMERA_MEDIA_CHOICES: { value: CameraMediaKind; label: string }[] = [
  { value: 'all', label: 'All media' },
  { value: 'streams', label: 'Streams' },
  { value: 'clips', label: 'Clips' },
  { value: 'snapshots', label: 'Snapshots' },
  { value: 'links', label: 'Provider links' },
];

interface CameraMedia {
  streams: boolean;
  clips: boolean;
  snapshots: boolean;
  links: boolean;
  label: string;
}
const mediaCache = new WeakMap<Camera, CameraMedia>();
const searchCache = new WeakMap<Camera, string>();

/** Match the player's allowlists and MP4 fallback, never infer live availability. */
export function cameraMedia(camera: Camera): CameraMedia {
  const previous = mediaCache.get(camera);
  if (previous) return previous;
  const video = isCameraStreamUrl(camera.stream_url, camera.stream_type === 'iframe');
  const snapshots = isCameraImageUrl(camera.snapshot_url);
  const clips = video && (camera.stream_type === 'mp4' || !camera.stream_type);
  const streams = video && !clips;
  const links = !snapshots && !video;
  const label = [
    snapshots ? 'Snapshot' : '',
    clips ? 'Video clip' : '',
    streams ? 'Stream' : '',
    links ? 'Provider link' : '',
  ]
    .filter(Boolean)
    .join(' / ');
  const result = { snapshots, clips, streams, links, label };
  mediaCache.set(camera, result);
  return result;
}

/** Only cached text is retained; replaced catalogue objects remain collectable. */
export function matchesCameraSearch(camera: Camera, query: string, providerName: string): boolean {
  if (!query) return true;
  let text = searchCache.get(camera);
  if (text === undefined) {
    text = `${camera.title} ${camera.provider}`.toLocaleLowerCase('en-GB');
    searchCache.set(camera, text);
  }
  return `${text} ${providerName}`.includes(query);
}

export function matchesCameraMedia(camera: Camera, kind: CameraMediaKind): boolean {
  return kind === 'all' || cameraMedia(camera)[kind];
}
