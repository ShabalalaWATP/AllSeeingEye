import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

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
