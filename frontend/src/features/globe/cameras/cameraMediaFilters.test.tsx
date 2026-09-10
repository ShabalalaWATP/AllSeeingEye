import { act, renderHook, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { fetchCameras, type Camera } from '@/lib/api/cameras';
import { cameraMedia, matchesCameraMedia } from './cameraMediaFilters';
import { useCameras } from './useCameras';

vi.mock('@/lib/api/cameras', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api/cameras')>()),
  fetchCameras: vi.fn(),
}));

const camera: Camera = {
  id: 'fintraffic:1',
  title: 'Road junction',
  provider: 'fintraffic',
  latitude: 0,
  longitude: 0,
  snapshot_url: null,
  source_url: 'https://www.digitraffic.fi/',
  attribution: 'Fintraffic',
  captured_at: null,
  coordinate_precision: 'exact',
};
const image = 'https://weathercam.digitraffic.fi/C0000101.jpg';
const stream = 'https://wzmedia.dot.ca.gov/example.m3u8';

it('uses approved media and renderer semantics rather than treating clips or blocked URLs as streams', () => {
  const snapshot = { ...camera, snapshot_url: image };
  const clip = { ...camera, stream_url: stream, stream_type: 'mp4' as const };
  const hls = { ...camera, stream_url: stream, stream_type: 'hls' as const };
  const fallback = { ...camera, stream_url: stream, stream_type: null };
  const frame = {
    ...camera,
    stream_url: 'https://www.youtube.com/embed/abc',
    stream_type: 'iframe' as const,
  };
  expect(cameraMedia(snapshot).label).toBe('Snapshot');
  expect(cameraMedia(clip).label).toBe('Video clip');
  expect(cameraMedia(hls).label).toBe('Stream');
  expect(cameraMedia(fallback).clips).toBe(true);
  expect(cameraMedia(frame).streams).toBe(true);
  expect(cameraMedia({ ...hls, snapshot_url: image }).label).toBe('Snapshot / Stream');
  expect(cameraMedia({ ...hls, stream_type: 'mjpeg' }).streams).toBe(true);
  for (const stream_url of [
    'http://wzmedia.dot.ca.gov/example.m3u8',
    'https://unapproved.test/live.m3u8',
  ]) {
    const blocked = { ...hls, stream_url };
    expect(matchesCameraMedia(blocked, 'streams')).toBe(false);
    expect(matchesCameraMedia(blocked, 'links')).toBe(true);
  }
  expect(cameraMedia({ ...snapshot, snapshot_url: 'https://unsafe.test/image.jpg' }).links).toBe(
    true,
  );
  expect(matchesCameraMedia(camera, 'all')).toBe(true);
  expect(cameraMedia(snapshot)).toBe(cameraMedia(snapshot));
  expect(cameraMedia({ ...snapshot })).not.toBe(cameraMedia(snapshot));
});

it('shares media and provider-name search with map data without fetching or reviving an excluded selection', async () => {
  const rows = [
    { ...camera, id: 'snapshot', snapshot_url: image },
    { ...camera, id: 'clip', stream_url: stream, stream_type: 'mp4' as const },
    { ...camera, id: 'hls', stream_url: stream, stream_type: 'hls' as const },
    { ...camera, id: 'link' },
  ];
  const fetch = vi.mocked(fetchCameras);
  fetch.mockResolvedValue({
    cameras: rows,
    providers: [
      {
        id: 'fintraffic',
        name: 'Finnish Road Cameras',
        status: 'available',
        count: rows.length,
        fetched_at: null,
        message: null,
      },
    ],
    fetched_at: '2026-09-10T00:00:00Z',
  });
  const { result, rerender } = renderHook(useCameras);
  expect(result.current.mediaKind).toBe('all');
  expect(result.current.visible).toEqual([]);
  act(() => result.current.setEnabled(true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  expect(result.current.visible).toHaveLength(4);
  fetch.mockClear();
  const stable = result.current.visible;
  rerender();
  expect(result.current.visible).toBe(stable);
  act(() => result.current.select(rows[0]!));
  act(() => result.current.setMediaKind('snapshots'));
  expect(result.current.selected?.id).toBe('snapshot');
  act(() => result.current.setMediaKind('streams'));
  expect(result.current.visible.map((item) => item.id)).toEqual(['hls']);
  expect(result.current.selected).toBeNull();
  act(() => result.current.setMediaKind('all'));
  expect(result.current.selected).toBeNull();
  act(() => result.current.setQuery('FINNISH ROAD'));
  expect(result.current.visible).toHaveLength(4);
  act(() => result.current.setMediaKind('clips'));
  expect(result.current.visible.map((item) => item.id)).toEqual(['clip']);
  act(() => result.current.setMediaKind('links'));
  expect(result.current.visible.map((item) => item.id)).toEqual(['link']);
  act(() => result.current.setQuery('Missing provider'));
  expect(result.current.visible).toEqual([]);
  expect(fetch).not.toHaveBeenCalled();
});
