/**
 * The axe helper must keep catching what jsdom can evaluate. If a jsdom or axe upgrade makes
 * a rule throw, axe files it as "incomplete" and the page checks would pass without it.
 */
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { axeViolations, expectNoAxeViolations } from '@/test/axe';

describe('axe helper', () => {
  it('reports focusable content inside an aria-hidden subtree with where and how to fix it', async () => {
    render(
      <main>
        <h1>Page</h1>
        <div aria-hidden="true">
          <button type="button">Hidden action</button>
        </div>
      </main>,
    );
    const [violation, ...rest] = await axeViolations();
    expect(rest).toEqual([]);
    expect(violation).toMatch(/^aria-hidden-focus \(serious\): /);
    expect(violation).toContain('at div[aria-hidden="true"]');
    expect(violation).toContain('https://dequeuniversity.com/rules/axe/');
  });

  it('runs the page-level rules that need hit testing in a browser', async () => {
    render(<p>No landmark and no heading</p>);
    const rules = (await axeViolations()).map((entry) => entry.split(' ')[0]);
    expect(rules).toEqual(
      expect.arrayContaining(['landmark-one-main', 'page-has-heading-one', 'region']),
    );
  });

  it('passes a well-formed page and honours a reasoned rule exclusion', async () => {
    render(
      <main>
        <h1>Page</h1>
        <button type="button">Act</button>
      </main>,
    );
    await expectNoAxeViolations();
    document.body.insertAdjacentHTML('beforeend', '<p>Outside</p>');
    await expectNoAxeViolations(document, { disable: ['region'] });
  });
});
