import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { EventRow } from './EventRow';
import { SourceText } from './SourceText';
import { sourceLanguageTag } from './sourceLanguage';

const ukrainian = liveEvent({
  id: 'uk',
  language: 'uk',
  title: 'Обстріл Харкова',
  title_en: null,
  url: 'https://example.com/uk',
});
const arabic = liveEvent({
  id: 'ar',
  language: 'ar',
  title: 'قصف في حلب',
  title_en: 'Shelling in Aleppo',
  url: null,
});
const undetermined = liveEvent({
  id: 'und',
  language: 'und',
  title: 'Mixed feed headline',
  title_en: null,
});

describe('sourceLanguageTag', () => {
  it('keeps plausible BCP 47 tags in canonical form', () => {
    expect(sourceLanguageTag('uk')).toBe('uk');
    expect(sourceLanguageTag('ar')).toBe('ar');
    expect(sourceLanguageTag('zh-hant-tw')).toBe('zh-Hant-TW');
    expect(sourceLanguageTag('pt_BR')).toBe('pt-BR');
  });

  it('drops undetermined, empty and arbitrary strings', () => {
    for (const value of [
      'und',
      'UND',
      'und-Latn',
      '',
      null,
      undefined,
      'english',
      'en" onmouseover="x',
      'x'.repeat(40),
      'e',
    ]) {
      expect(sourceLanguageTag(value)).toBeUndefined();
    }
  });
});

describe('SourceText', () => {
  it('marks a known language and always sets automatic direction', () => {
    render(
      <>
        <SourceText language="uk">Обстріл</SourceText>
        <SourceText language="und" as="p">
          Unknown
        </SourceText>
        <SourceText language="not a tag">Rejected</SourceText>
      </>,
    );
    expect(screen.getByText('Обстріл')).toHaveAttribute('lang', 'uk');
    expect(screen.getByText('Обстріл')).toHaveAttribute('dir', 'auto');
    const unknown = screen.getByText('Unknown');
    expect(unknown.tagName).toBe('P');
    expect(unknown).not.toHaveAttribute('lang');
    expect(unknown).toHaveAttribute('dir', 'auto');
    expect(screen.getByText('Rejected')).not.toHaveAttribute('lang');
  });
});

describe('EventRow language marking', () => {
  function renderRows() {
    render(
      <MemoryRouter>
        <ul>
          <EventRow event={ukrainian} />
          <EventRow event={arabic} />
          <EventRow event={undetermined} />
        </ul>
      </MemoryRouter>,
    );
    return screen.getAllByRole('listitem');
  }

  it('marks an original-language title with lang and dir', () => {
    const [uk] = renderRows();
    const title = within(uk!).getByText('Обстріл Харкова');
    expect(title).toHaveAttribute('lang', 'uk');
    expect(title).toHaveAttribute('dir', 'auto');
  });

  it('shows the English title without a foreign lang and marks und with direction only', () => {
    const [, ar, und] = renderRows();
    expect(within(ar!).getByText('Shelling in Aleppo')).not.toHaveAttribute('lang', 'ar');
    const unknown = within(und!).getByText('Mixed feed headline');
    expect(unknown).not.toHaveAttribute('lang');
    expect(unknown).toHaveAttribute('dir', 'auto');
  });

  it('never mixes the English research label with a title in another language', () => {
    const [uk, ar, und] = renderRows();
    const ukLink = within(uk!).getByRole('link', { name: /^Research this report/ });
    expect(ukLink).toHaveAccessibleName('Research this report');
    expect(ukLink).not.toHaveAccessibleName(/Обстріл/);
    expect(ukLink).toHaveAccessibleDescription('Обстріл Харкова');
    expect(within(ar!).getByRole('link', { name: /^Research this report/ })).toHaveAccessibleName(
      'Research this report: Shelling in Aleppo',
    );
    expect(within(und!).getByRole('link', { name: /^Research this report/ })).toHaveAccessibleName(
      'Research this report',
    );
  });
});
