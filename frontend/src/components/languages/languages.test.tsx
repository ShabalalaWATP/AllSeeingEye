import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import catalogue from '@/test/fixtures.languages.json';
import { server } from '@/test/server';
import { NarrativeLanguageField } from './NarrativeLanguageField';
import { SourceLanguagePicker } from './SourceLanguagePicker';

describe('language capability controls', () => {
  it('offers Persian and explicit Chinese scripts while retaining legacy Chinese', async () => {
    const changed = vi.fn();
    render(<NarrativeLanguageField value="zh" onChange={changed} />);
    await screen.findByRole('option', { name: 'Persian' });
    expect(screen.getByRole('option', { name: 'Chinese (unspecified script)' })).toHaveValue('zh');
    expect(screen.getByRole('option', { name: 'Chinese (Simplified)' })).toHaveValue('zh-Hans');
    expect(screen.getByRole('option', { name: 'Chinese (Traditional)' })).toHaveValue('zh-Hant');
    expect(
      screen.queryByRole('option', { name: /mainland China search edition/ }),
    ).not.toBeInTheDocument();
    await userEvent.setup().selectOptions(screen.getByLabelText('Narrative language'), 'fa');
    expect(changed).toHaveBeenCalledWith('fa');
  });

  it('keeps the selected value while a catalogue failure is retried', async () => {
    server.use(
      http.get('/api/me/profile/languages', () => new HttpResponse(null, { status: 503 })),
    );
    render(<NarrativeLanguageField value="zh-Hant" onChange={vi.fn()} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Your selection has been kept');
    expect(screen.getByLabelText('Narrative language')).toHaveValue('zh-Hant');
    expect(screen.getByLabelText('Narrative language')).toBeDisabled();
    server.use(http.get('/api/me/profile/languages', () => HttpResponse.json(catalogue)));
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry languages' }));
    await waitFor(() => expect(screen.getByLabelText('Narrative language')).toBeEnabled());
  });

  it('keeps script and regional source choices separate and explains unmapped coverage', async () => {
    const changed = vi.fn();
    render(<SourceLanguagePicker selected={['fa', 'zh-Hant']} onChange={changed} />);
    expect(await screen.findByRole('checkbox', { name: 'Persian' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Chinese (Traditional)' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Taiwan search edition/ })).not.toBeChecked();
    expect(screen.getByText(/without substituting a country or script/)).toBeVisible();
    await userEvent.setup().click(screen.getByRole('checkbox', { name: /Taiwan search edition/ }));
    expect(changed).toHaveBeenCalledWith(['fa', 'zh-Hant', 'zh-TW']);
  });

  it('prevents adding a ninth source language without losing existing selections', async () => {
    render(
      <SourceLanguagePicker
        selected={['en', 'fr', 'de', 'es', 'ar', 'fa', 'ru', 'uk']}
        onChange={vi.fn()}
      />,
    );
    expect(await screen.findByRole('checkbox', { name: 'Chinese (Simplified)' })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: 'English' })).toBeEnabled();
    expect(screen.getByRole('checkbox', { name: 'English' })).toBeChecked();
  });
});
