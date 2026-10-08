import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { newBriefDraft, nextRequirementId } from '@/lib/researchBriefDraft';

import { BriefQuestionEditor } from './BriefQuestionEditor';

function editor(initial: BriefDraft = newBriefDraft()) {
  let current = initial;
  function Harness() {
    const [draft, setDraft] = useState(initial);
    return (
      <BriefQuestionEditor
        draft={draft}
        change={(next) => {
          current = next;
          setDraft(next);
        }}
      />
    );
  }
  render(<Harness />);
  return () => current;
}

describe('nextRequirementId', () => {
  it('numbers from the row count and skips any ID already in use', () => {
    expect(nextRequirementId([])).toBe('req-1');
    expect(nextRequirementId([{ id: 'req-1' }])).toBe('req-2');
    expect(nextRequirementId([{ id: 'req-2' }, { id: 'req-3' }])).toBe('req-4');
    expect(nextRequirementId([{ id: 'custom' }, { id: 'req-2' }])).toBe('req-3');
  });
});

describe('BriefQuestionEditor', () => {
  it('never creates a duplicate ID after a requirement is removed', () => {
    const draft = editor();
    const add = () => fireEvent.click(screen.getByRole('button', { name: 'Add requirement' }));
    add();
    add();
    add();
    fireEvent.click(screen.getByRole('button', { name: 'Remove requirement 1' }));
    add();
    const ids = draft().question.requirements.map((row) => row.id);
    expect(ids).toEqual(['req-2', 'req-3', 'req-4']);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
