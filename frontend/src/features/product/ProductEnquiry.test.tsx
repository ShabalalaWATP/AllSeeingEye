import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it('keeps the loaded public route hidden until configuration explicitly enables it', async () => {
  let release!: () => void;
  let requested = false;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    http.get('/api/site', async () => {
      requested = true;
      await pending;
      return HttpResponse.json({
        product_page_enabled: false,
        enterprise_enquiries_enabled: false,
      });
    }),
  );
  renderApp('/enterprise', 'anonymous');
  await waitFor(() => expect(requested).toBe(true));
  expect(screen.queryByRole('heading', { level: 1, name: /The All Seeing Eye/ })).toBeNull();
  expect(screen.queryByRole('form', { name: 'Enquire about self-hosting' })).toBeNull();
  expect(document.querySelector('link[rel="canonical"]')).toBeNull();
  release();
  await screen.findByRole('heading', { name: /not found/i });
  expect(screen.queryByRole('form', { name: 'Enquire about self-hosting' })).toBeNull();
});

it.each([
  { product: true, enquiries: false, story: true, form: false },
  { product: false, enquiries: true, story: true, form: true },
  { product: true, enquiries: true, story: true, form: true },
  { product: false, enquiries: false, story: false, form: false },
])('coordinates product=$product and enquiries=$enquiries', async (flags) => {
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({
        product_page_enabled: flags.product,
        enterprise_enquiries_enabled: flags.enquiries,
      }),
    ),
  );
  renderApp('/enterprise', 'anonymous');
  if (flags.story) await screen.findByRole('heading', { level: 1, name: /The All Seeing Eye/ });
  else await screen.findByRole('heading', { name: /not found/i });
  expect(screen.queryByRole('form', { name: 'Enquire about self-hosting' }) !== null).toBe(
    flags.form,
  );
});
