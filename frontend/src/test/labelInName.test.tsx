import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { accessibleName, labelInName, visibleText } from './labelInName';

describe('label in name helper', () => {
  it('reads visible text without hidden or screen-reader-only parts', () => {
    render(
      <button type="button">
        <svg aria-hidden="true">
          <title>Icon</title>
        </svg>
        Save <span className="sr-only">report</span>
        <span hidden>draft</span>
      </button>,
    );
    const button = screen.getByRole('button');
    expect(visibleText(button)).toBe('Save');
    expect(accessibleName(button)).toBe('Save report');
    expect(labelInName(button)).toBe(true);
  });

  it('ignores case and punctuation but not order', () => {
    render(
      <>
        <a href="/a" aria-label="ops room, esc to exit">
          Ops room · Esc to exit
        </a>
        <a href="/b" aria-label="Exit ops room">
          Ops room · Esc to exit
        </a>
        <button type="button" aria-label="Menu">
          <svg aria-hidden="true" />
        </button>
      </>,
    );
    const [matching, reordered] = screen.getAllByRole('link');
    expect(matching && labelInName(matching)).toBe(true);
    expect(reordered && labelInName(reordered)).toBe(false);
    // An icon-only control has no visible label to contain.
    expect(labelInName(screen.getByRole('button'))).toBe(false);
  });
});
