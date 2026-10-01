import { screen, waitFor, within } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { describeBriefRejection } from './briefRejection';

const rejected = (fields: Record<string, string>) =>
  new ApiError(422, 'validation_error', 'The Research Brief is invalid.', fields);

describe('describeBriefRejection', () => {
  it('names the rejected fields and the stage that holds them', () => {
    expect(describeBriefRejection(rejected({ 'scope.country_isos': 'Invalid value.' }))).toEqual({
      message: 'Review these fields: Country codes: Invalid value.',
      step: 'scope',
    });
    expect(describeBriefRejection(rejected({ 'question.main': 'Invalid value.' }))).toEqual({
      message: 'Review these fields: Main research question: Invalid value.',
      step: 'brief',
    });
    expect(describeBriefRejection(rejected({ 'limits.max_sources': 'Too high.' }))).toEqual({
      message: 'Review these fields: Limits: Too high.',
      step: 'depth',
    });
  });

  it('keeps the generic message with unknown paths and for other failures', () => {
    expect(describeBriefRejection(rejected({ identity: 'Immutable.' }))).toEqual({
      message: 'The Research Brief is invalid. Identity: Immutable.',
      step: null,
    });
    expect(describeBriefRejection(new ApiError(503, 'x', 'Unavailable.'))).toEqual({
      message: 'Unavailable.',
      step: null,
    });
  });
});

it('shows a rejected brief field in the editor summary and opens its stage', async () => {
  server.use(
    http.post('/api/research/briefs', () =>
      apiError(422, 'validation_error', 'The Research Brief is invalid.', {
        'scope.country_isos': 'Invalid or unsupported value.',
      }),
    ),
  );
  const { user } = renderApp('/research?brief=new', 'user');
  const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
  await user.type(editor.getByLabelText('Brief title'), 'Port intelligence');
  await user.type(editor.getByLabelText('Main research question'), 'What changed at the port?');
  await user.click(editor.getByRole('button', { name: 'Add requirement' }));
  await user.type(editor.getByLabelText('Requirement 1 question'), 'Has throughput changed?');
  await user.click(editor.getByRole('button', { name: 'Save brief' }));
  const alert = await editor.findByRole('alert');
  expect(alert).toHaveTextContent('Country codes: Invalid or unsupported value.');
  expect(alert).not.toHaveTextContent('The Research Brief is invalid.');
  await waitFor(() =>
    expect(editor.getByLabelText('Country codes, comma separated')).toBeVisible(),
  );
});
