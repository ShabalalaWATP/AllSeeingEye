import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import {
  fetchUkraineBoard,
  fetchUkraineControl,
  fetchUkraineReference,
  referenceImagePath,
} from '@/lib/api/ukraine';
import { ukraineBoard, ukraineControl } from '@/test/fixtures.ukraine';
import { ukraineReference } from '@/test/fixtures.ukraineReference';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { ReferenceImage, loadReferenceImage } from './ReferenceImage';
import { REFRESH_MS, useUkraineBoard } from './useUkraineBoard';

beforeAll(() => {
  applySession('user');
  if (!('createObjectURL' in URL)) {
    Object.assign(URL, { createObjectURL: () => 'blob:unit', revokeObjectURL: () => undefined });
  }
});

afterEach(() => {
  vi.useRealTimers();
});

describe('Ukraine API client', () => {
  it('fetches each resource with and without an abort signal', async () => {
    const controller = new AbortController();
    expect((await fetchUkraineBoard(controller.signal)).day_number).toBe(ukraineBoard.day_number);
    expect((await fetchUkraineBoard()).claims).toHaveLength(2);
    expect((await fetchUkraineControl(controller.signal)).settlements).toHaveLength(
      ukraineControl.settlements.length,
    );
    expect((await fetchUkraineControl()).outlines).toHaveLength(1);
    expect((await fetchUkraineReference(controller.signal)).equipment).toHaveLength(
      ukraineReference.equipment.length,
    );
    expect((await fetchUkraineReference()).phases).toHaveLength(2);
    expect(referenceImagePath('ru-t-90m')).toBe('/api/conflicts/ukraine/images/ru-t-90m.jpg');
  });

  it('rejects a board whose claims carry negative counts', async () => {
    server.use(
      http.get('/api/conflicts/ukraine', () =>
        HttpResponse.json({
          ...ukraineBoard,
          claims: [{ ...ukraineBoard.claims[0], totals: { tanks: -1 } }],
        }),
      ),
    );
    await expect(fetchUkraineBoard()).rejects.toThrow();
  });
});

describe('reference images', () => {
  it('shares one fetch per image id and forgets a failed one', async () => {
    const good = vi.fn(() => Promise.resolve(new Blob(['x'], { type: 'image/jpeg' })));
    const first = await loadReferenceImage('shared-one', good);
    const second = await loadReferenceImage('shared-one', good);
    expect(first).toBe(second);
    expect(good).toHaveBeenCalledTimes(1);
    const bad = vi.fn(() => Promise.reject(new Error('offline')));
    await expect(loadReferenceImage('broken-one', bad)).rejects.toThrow('offline');
    await Promise.resolve();
    await expect(loadReferenceImage('broken-one', bad)).rejects.toThrow('offline');
    expect(bad).toHaveBeenCalledTimes(2);
  });

  it('renders nothing while loading, without metadata, or after a failure', async () => {
    const meta = ukraineReference.images['ru-t-90m'];
    const fetcher = () => Promise.resolve(new Blob(['x'], { type: 'image/jpeg' }));
    const { container, rerender } = render(
      <ReferenceImage imageId="ru-t-90m" meta={meta} alt="T-90M" fetcher={fetcher} />,
    );
    expect(container.querySelector('img')).toBeNull();
    expect(await screen.findByRole('img', { name: 'T-90M' })).toHaveAttribute('width', '480');
    rerender(<ReferenceImage imageId="ru-t-90m" meta={undefined} alt="T-90M" fetcher={fetcher} />);
    expect(container.querySelector('img')).toBeNull();
    const failing = () => Promise.reject(new Error('gone'));
    render(<ReferenceImage imageId="missing-two" meta={meta} alt="Gone" fetcher={failing} />);
    await waitFor(() => expect(screen.queryByRole('img', { name: 'Gone' })).toBeNull());
  });
});

describe('board refresh', () => {
  it('reloads on the timer only while the document is visible', async () => {
    vi.useFakeTimers();
    const load = vi.fn(() => Promise.resolve(ukraineBoard));
    const { result } = renderHook(() => useUkraineBoard(load));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(load).toHaveBeenCalledTimes(1);
    expect(result.current.data?.board.day_number).toBe(1663);
    const visibility = vi.spyOn(document, 'visibilityState', 'get');
    visibility.mockReturnValue('hidden');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REFRESH_MS);
    });
    expect(load).toHaveBeenCalledTimes(1);
    visibility.mockReturnValue('visible');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REFRESH_MS);
    });
    expect(load).toHaveBeenCalledTimes(2);
    visibility.mockRestore();
  });
});
