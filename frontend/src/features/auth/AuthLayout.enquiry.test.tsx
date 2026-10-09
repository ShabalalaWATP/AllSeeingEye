import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

it.each([false, true])(
  'offers organisational self-hosting when enquiries are enabled (product=%s)',
  async (product) => {
    const scroll = vi.spyOn(Element.prototype, 'scrollIntoView');
    server.use(
      http.get('/api/site', () =>
        HttpResponse.json({ product_page_enabled: product, enterprise_enquiries_enabled: true }),
      ),
    );
    const { user } = renderApp('/login', 'anonymous');
    const links = await screen.findAllByRole('link', { name: 'Self-hosting for organisations' });
    for (const link of links) expect(link).toHaveAttribute('href', '/enterprise#contact');
    // The new public navigation lives outside the sign-in form's control sequence.
    screen.getByLabelText('Email').focus();
    await user.tab();
    expect(screen.getByLabelText('Password')).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Show password' })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Sign in' })).toHaveFocus();
    await user.click(links[0]!);
    expect(
      await screen.findByRole('form', { name: 'Enquire about self-hosting' }),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole('heading', {
          name: 'Bring The All Seeing Eye inside your organisation.',
        }),
      ).toHaveFocus(),
    );
    expect(scroll.mock.contexts).toContain(document.getElementById('contact'));
  },
);

it('preserves product discovery but hides enquiry navigation when enquiries are disabled', async () => {
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({ product_page_enabled: true, enterprise_enquiries_enabled: false }),
    ),
  );
  renderApp('/login', 'anonymous');
  await screen.findByRole('link', { name: 'Discover what it can do' });
  expect(screen.queryByRole('link', { name: 'Self-hosting for organisations' })).toBeNull();
});
