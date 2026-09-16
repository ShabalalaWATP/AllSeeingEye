import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it } from 'vitest';

import {
  ukraineDigest,
  ukraineDigestGenerating,
  ukraineDigestNone,
  ukraineDigestRejected,
  ukraineDigestStale,
  ukraineDigestUnavailable,
} from '@/test/fixtures.ukraineDigest';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

import { DigestPanel } from './DigestPanel';

const DIGEST = '/api/conflicts/ukraine/digest';

function serve(body: object, status = 200) {
  server.use(http.get(DIGEST, () => HttpResponse.json(body, { status })));
}

function renderPanel(session: 'user' | 'admin' = 'user') {
  applySession(session);
  const user = userEvent.setup();
  return { ...render(<DigestPanel />), user };
}

beforeAll(async () => {
  await import('./UkrainePage');
});

describe('Ukraine AI digest panel', () => {
  it('shows the period, both strands, the sources each change rests on and the provenance', async () => {
    renderPanel();
    expect(
      await screen.findByRole('heading', { name: 'AI digest' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByText('Fortnight to 16 September 2026')).toBeInTheDocument();
    expect(screen.getByText(/Nothing in it is verified by this application/)).toBeInTheDocument();
    const battlefield = within(screen.getByRole('list', { name: 'Battlefield changes' }));
    expect(battlefield.getByText(/continued Russian attacks near the eastern city/)).toBeVisible();
    const sources = battlefield.getAllByRole('list', { name: 'Sources for this change' })[0];
    expect(
      within(sources!).getByRole('link', {
        name: 'Russian offensive campaign assessment, 15 September 2026',
      }),
    ).toHaveAttribute('href', 'https://understandingwar.org/example');
    // A citation without a link is still shown, as text rather than an invented link.
    expect(within(sources!).getByText(/assessment, later, 13 September 2026/)).toBeVisible();
    expect(
      within(screen.getByRole('list', { name: 'Political changes' })).getByText(
        /European ministers met to discuss further funding/,
      ),
    ).toBeVisible();
    expect(screen.getByRole('list', { name: 'What to watch' })).toHaveTextContent(
      /strikes on energy infrastructure continue into winter/,
    );
    expect(screen.getByRole('list', { name: 'Caveats' })).toHaveTextContent(/cannot verify/);
    await userEvent.click(screen.getByText('How this digest was made'));
    expect(screen.getByText('fixture-assessment-model')).toBeVisible();
    expect(screen.getByText(/2 September 2026 to 16 September 2026/)).toBeVisible();
    expect(screen.getByText(/9400 in, 1100 out/)).toBeVisible();
  });

  it('offers the previous digest behind a selector', async () => {
    const { user } = renderPanel();
    const selector = await screen.findByRole('combobox', {}, { timeout: 5000 });
    expect(selector).toHaveDisplayValue('Fortnight to 16 September 2026 (latest)');
    await user.selectOptions(selector, '2026-09-02T06:30:00Z');
    expect(
      await screen.findByText('Fortnight to 2 September 2026', { selector: 'span' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText('The previous fortnight showed little verifiable change on the ground.'),
    ).toBeVisible();
  });

  it('says nothing has been written yet rather than inventing a digest', async () => {
    serve(ukraineDigestNone);
    renderPanel();
    expect(await screen.findByText(/No digest has been written yet/)).toBeVisible();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('shows that a digest is being written', async () => {
    serve(ukraineDigestGenerating);
    renderPanel();
    expect(await screen.findByText(/A digest is being written/)).toBeVisible();
  });

  it('gives the honest reason when no model is available', async () => {
    serve(ukraineDigestUnavailable);
    renderPanel();
    expect(await screen.findByText(/No model is assigned/)).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('No digest is available');
  });

  it('says plainly when the checks rejected the model answer', async () => {
    serve(ukraineDigestRejected);
    renderPanel();
    expect(await screen.findByText('The last attempt was not stored')).toBeVisible();
    expect(await screen.findByText(/nothing was saved/)).toBeVisible();
  });

  it('marks a digest whose fortnight has ended as stale but still shows it', async () => {
    serve(ukraineDigestStale);
    renderPanel();
    expect(await screen.findByText(/covers a fortnight that has already ended/)).toBeVisible();
    expect(screen.getByRole('list', { name: 'Battlefield changes' })).toBeInTheDocument();
  });

  it('surfaces a load failure without an error page', async () => {
    serve({ error: { code: 'server_error', message: 'The digest could not be read.' } }, 500);
    renderPanel();
    expect(await screen.findByRole('heading', { name: 'AI digest' })).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent(/digest could not be read/);
  });

  it('hides the refresh control from readers and offers it to administrators', async () => {
    serve(ukraineDigestNone);
    renderPanel('user');
    await screen.findByText(/No digest has been written yet/);
    expect(screen.queryByRole('button', { name: 'Write a new digest' })).not.toBeInTheDocument();
  });

  it('lets an administrator ask for a digest and shows the answer', async () => {
    serve(ukraineDigestNone);
    let asked = 0;
    server.use(
      http.post('/api/conflicts/ukraine/digest/refresh', () => {
        asked += 1;
        return HttpResponse.json(ukraineDigest);
      }),
    );
    const { user } = renderPanel('admin');
    await user.click(await screen.findByRole('button', { name: 'Write a new digest' }));
    await waitFor(() => expect(asked).toBe(1));
    expect(await screen.findByRole('list', { name: 'Battlefield changes' })).toBeInTheDocument();
  });

  it('reports a refused refresh without losing the panel', async () => {
    serve(ukraineDigestNone);
    server.use(
      http.post('/api/conflicts/ukraine/digest/refresh', () =>
        HttpResponse.json(
          { error: { code: 'rate_limited', message: 'Too many refreshes. Try later.' } },
          { status: 429 },
        ),
      ),
    );
    const { user } = renderPanel('admin');
    await user.click(await screen.findByRole('button', { name: 'Write a new digest' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Too many attempts/);
    expect(screen.getByRole('heading', { name: 'AI digest' })).toBeInTheDocument();
  });

  it('is mounted on the Ukraine page with its own navigation entry', async () => {
    renderApp('/conflicts/ukraine', 'user');
    expect(
      await screen.findByRole('heading', { name: 'AI digest' }, { timeout: 5000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'AI digest' })).toHaveAttribute('href', '#digest');
  });
});
