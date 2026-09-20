import { fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { savedMapFixture } from '@/test/fixtures.savedMaps';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const viewId = '00000000-0000-4000-8000-000000000001';
const revisionId = '00000000-0000-4000-8000-000000000002';
const path = `/research?map_view=${viewId}&map_revision=${revisionId}`;
const from = 'Acquisition / publication from (UTC)';
const until = 'Acquisition / publication until (UTC, exclusive)';

async function mount() {
  let calls = 0;
  server.use(
    http.get('/api/map/views/:view/revisions/:revision', () =>
      HttpResponse.json({
        ...savedMapFixture,
        view: { ...savedMapFixture.view, id: viewId },
        revision: { ...savedMapFixture.revision, id: revisionId, view_id: viewId },
      }),
    ),
    http.post('/api/report-jobs', () => {
      calls++;
      return HttpResponse.json({}, { status: 500 });
    }),
  );
  renderApp(path, 'user');
  await waitFor(() => expect(screen.getByLabelText('Your area research question')).toBeEnabled());
  return () => calls;
}

it.each([
  ['question', 'Enter a research question.'],
  ['dates', 'Choose a positive UTC interval'],
  ['future', 'future'],
  ['no preview', 'Preview this area and interval'],
  ['invalid historical years', 'Choose valid project years'],
] as const)('rejects %s even if submission bypasses the disabled button', async (kind, message) => {
  const calls = await mount();
  if (kind !== 'question')
    fireEvent.change(screen.getByLabelText('Your area research question'), {
      target: { value: 'What was observed?' },
    });
  if (kind === 'future' || kind === 'no preview') {
    const year = kind === 'future' ? '2099' : '2020';
    fireEvent.change(screen.getByLabelText(from), { target: { value: `${year}-01-01T00:00` } });
    fireEvent.change(screen.getByLabelText(until), { target: { value: `${year}-01-02T00:00` } });
  }
  if (kind === 'invalid historical years') {
    fireEvent.change(screen.getByLabelText('Research period'), { target: { value: 'history' } });
    fireEvent.change(screen.getByLabelText('Last commitment year'), { target: { value: '1999' } });
  }
  fireEvent.submit(screen.getByRole('form', { name: 'Research a saved area' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(message);
  expect(calls()).toBe(0);
});
