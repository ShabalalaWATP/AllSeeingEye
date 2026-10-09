import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/server';

import { useSiteFacts } from './useSiteFacts';

describe('useSiteFacts', () => {
  it('exposes the explicit enquiry flag without revealing configuration', async () => {
    server.use(
      http.get('/api/site', () =>
        HttpResponse.json({
          product_page_enabled: true,
          enterprise_enquiries_enabled: true,
          enterprise_enquiry_retention_days: 90,
        }),
      ),
    );
    const hook = renderHook(() => useSiteFacts());
    await waitFor(() =>
      expect(hook.result.current).toEqual({
        status: 'ready',
        facts: {
          product_page_enabled: true,
          enterprise_enquiries_enabled: true,
          enterprise_enquiry_retention_days: 90,
        },
      }),
    );
  });

  it('treats a failed request as off without remembering the failure', async () => {
    let calls = 0;
    server.use(
      http.get('/api/site', () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 503 })
          : HttpResponse.json({ product_page_enabled: true });
      }),
    );
    const first = renderHook(() => useSiteFacts());
    await waitFor(() =>
      expect(first.result.current).toEqual({
        status: 'ready',
        facts: {
          product_page_enabled: false,
          enterprise_enquiries_enabled: false,
          enterprise_enquiry_retention_days: 365,
        },
      }),
    );
    const second = renderHook(() => useSiteFacts());
    await waitFor(() =>
      expect(second.result.current).toEqual({
        status: 'ready',
        facts: {
          product_page_enabled: true,
          enterprise_enquiries_enabled: false,
          enterprise_enquiry_retention_days: 365,
        },
      }),
    );
    expect(calls).toBe(2);
  });

  it('asks once for every component on a page', async () => {
    let calls = 0;
    server.use(
      http.get('/api/site', () => {
        calls += 1;
        return HttpResponse.json({ product_page_enabled: true });
      }),
    );
    const a = renderHook(() => useSiteFacts());
    const b = renderHook(() => useSiteFacts());
    await waitFor(() => expect(a.result.current.status).toBe('ready'));
    await waitFor(() => expect(b.result.current.status).toBe('ready'));
    expect(calls).toBe(1);
  });
});
