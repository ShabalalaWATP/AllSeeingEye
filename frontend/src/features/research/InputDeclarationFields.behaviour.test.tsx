import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it } from 'vitest';

import type { DeclarationTargets } from '@/lib/api/inputDeclarations';

import { emptyDeclaration, InputDeclarationFields } from './InputDeclarationFields';
import type { DeclarationDraft } from './InputDeclarationFields';

const targets: DeclarationTargets['targets'] = [
  {
    event_id: 'first',
    content_hash: 'a'.repeat(64),
    title: 'Original first title',
    summary: 'First snippet',
    language: 'fa',
    transformations: [],
    source_dates: [],
  },
  {
    event_id: 'second',
    content_hash: 'b'.repeat(64),
    title: 'Original second title',
    summary: null,
    language: 'ar',
    transformations: [],
    source_dates: [],
  },
];

function editor(initial: DeclarationDraft = emptyDeclaration()) {
  let current = initial;
  function Harness() {
    const [value, setValue] = useState(initial);
    return (
      <InputDeclarationFields
        value={value}
        targets={targets}
        index={1}
        update={(next) => {
          current = next;
          setValue(next);
        }}
      />
    );
  }
  return { ...render(<Harness />), user: userEvent.setup(), draft: () => current };
}

it('resets declarations and derives the new language when changing or clearing the passage', async () => {
  const view = editor({
    ...emptyDeclaration(),
    eventId: 'first',
    transform: true,
    transformed: 'Previous rendering',
    sourceLanguage: 'fa',
    targetLanguage: 'en',
    date: true,
    rawDate: '1404-01-01',
  });
  expect(screen.getByText('Original first title', { selector: 'p' })).toBeVisible();
  await view.user.selectOptions(screen.getByLabelText('Declaration 2 passage'), 'second');
  expect(view.draft()).toEqual({ ...emptyDeclaration(), eventId: 'second', sourceLanguage: 'ar' });
  expect(screen.queryByLabelText('Declaration 2 transformed text')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Declaration 2 raw source date')).not.toBeInTheDocument();
  await view.user.selectOptions(screen.getByLabelText('Declaration 2 original field'), 'summary');
  expect(screen.getByText('Choose a non-empty original field.')).toBeVisible();
  await view.user.selectOptions(screen.getByLabelText('Declaration 2 passage'), '');
  expect(view.draft()).toEqual(emptyDeclaration());
});

it('clears field-specific rendering and dates when switching between title and snippet', async () => {
  const view = editor({
    ...emptyDeclaration(),
    eventId: 'first',
    transform: true,
    transformed: 'Title rendering',
    date: true,
    rawDate: '2026-09-14',
    sourceLanguage: 'fa',
  });
  await view.user.selectOptions(screen.getByLabelText('Declaration 2 original field'), 'summary');
  expect(screen.getByText('First snippet')).toBeVisible();
  expect(view.draft()).toMatchObject({
    field: 'summary',
    transformed: '',
    rawDate: '',
    sourceLanguage: 'fa',
  });
  await view.user.type(
    screen.getByLabelText('Declaration 2 transformed text'),
    'Snippet rendering',
  );
  await view.user.type(screen.getByLabelText('Declaration 2 raw source date'), '2026-09-15');
  await view.user.selectOptions(screen.getByLabelText('Declaration 2 original field'), 'title');
  expect(view.draft()).toMatchObject({ field: 'title', transformed: '', rawDate: '' });
});

it('records explicit language, script and method choices without treating them as verified output', async () => {
  const view = editor({ ...emptyDeclaration(), eventId: 'first' });
  await view.user.click(screen.getByLabelText('Declaration 2: supply text transformation'));
  await view.user.selectOptions(
    screen.getByLabelText('Declaration 2 transformation kind'),
    'translation',
  );
  const fields = [
    ['source language', 'fa'],
    ['target language', 'en'],
    ['source script', 'Arab'],
    ['target script', 'Latn'],
    ['method', 'Operator-reviewed rendering'],
    ['transformed text', 'Complete translated title'],
  ];
  for (const [label, text] of fields) {
    fireEvent.change(screen.getByLabelText(`Declaration 2 ${label}`), { target: { value: text } });
  }
  expect(view.draft()).toMatchObject({
    kind: 'translation',
    sourceLanguage: 'fa',
    targetLanguage: 'en',
    sourceScript: 'Arab',
    targetScript: 'Latn',
    method: 'Operator-reviewed rendering',
    transformed: 'Complete translated title',
  });
  expect(screen.getByText(/your declaration, not a verified model result/)).toBeVisible();
  await view.user.selectOptions(
    screen.getByLabelText('Declaration 2 transformation kind'),
    'transliteration',
  );
  expect(view.draft().kind).toBe('transliteration');
  await view.user.click(screen.getByLabelText('Declaration 2: supply text transformation'));
  expect(screen.queryByLabelText('Declaration 2 method')).not.toBeInTheDocument();
  expect(view.draft().transform).toBe(false);
});

it('preserves raw date text while explicitly changing calendars and date roles', async () => {
  const view = editor({ ...emptyDeclaration(), eventId: 'first' });
  await view.user.click(screen.getByLabelText('Declaration 2: declare a source date'));
  await view.user.type(screen.getByLabelText('Declaration 2 raw source date'), '1404-01-01');
  for (const calendar of ['gregorian', 'solar_hijri_icu33', 'unknown'] as const) {
    await view.user.selectOptions(screen.getByLabelText('Declaration 2 calendar'), calendar);
    expect(view.draft().calendar).toBe(calendar);
    expect(view.draft().rawDate).toBe('1404-01-01');
  }
  for (const role of ['occurrence', 'record_validity', 'publication'] as const) {
    await view.user.selectOptions(screen.getByLabelText('Declaration 2 date role'), role);
    expect(view.draft().role).toBe(role);
  }
  expect(screen.getByText(/No calendar or timezone is inferred/)).toBeVisible();
  await view.user.click(screen.getByLabelText('Declaration 2: declare a source date'));
  expect(view.draft().date).toBe(false);
  expect(screen.queryByLabelText('Declaration 2 raw source date')).not.toBeInTheDocument();
});
