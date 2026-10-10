import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { resetSiteFacts } from '@/lib/useSiteFacts';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const CONTACT_HEADING = 'Bring The All Seeing Eye inside your organisation.';

beforeEach(() => {
  server.use(
    http.get('/api/site', () =>
      HttpResponse.json({ product_page_enabled: true, enterprise_enquiries_enabled: true }),
    ),
  );
});
afterEach(() => resetSiteFacts());

describe('public contact navigation', () => {
  it.each(['header', 'hero'] as const)(
    'moves keyboard focus from the %s contact link',
    async (source) => {
      const { user, router } = renderApp('/enterprise', 'anonymous');
      const heading = await screen.findByRole('heading', { name: CONTACT_HEADING });
      const area =
        source === 'header'
          ? screen.getByRole('link', { name: 'The All Seeing Eye, back to top' }).closest('header')
          : screen.getByRole('region', { name: 'The All Seeing Eye' });
      if (area === null) throw new Error('The public contact navigation area is missing.');
      const link = within(area).getByRole('link', { name: 'Talk to us' });

      await user.click(link);
      await waitFor(() => expect(router.state.location.hash).toBe('#contact'));
      expect(heading).toHaveFocus();

      // Activating the same target again still restores a useful keyboard position.
      await user.click(screen.getByRole('textbox', { name: 'Name' }));
      await user.click(link);
      await waitFor(() => expect(heading).toHaveFocus());
    },
  );

  it('focuses the heading after a direct lazy route load', async () => {
    renderApp('/enterprise#contact', 'anonymous');
    const heading = await screen.findByRole('heading', { name: CONTACT_HEADING });
    await waitFor(() => expect(heading).toHaveFocus());
  });
});
