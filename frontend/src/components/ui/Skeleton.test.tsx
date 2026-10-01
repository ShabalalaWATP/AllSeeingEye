import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Skeleton } from './Skeleton';

describe('Skeleton', () => {
  it('draws the requested lines, hidden from assistive technology', () => {
    const { container } = render(<Skeleton lines={5} className="mt-2" />);
    const skeleton = container.firstElementChild;
    expect(skeleton).toHaveAttribute('aria-hidden', 'true');
    expect(skeleton).toHaveClass('mt-2');
    expect(skeleton?.children).toHaveLength(5);
    expect(skeleton?.children[4]).toHaveClass('animate-pulse', 'w-full');
  });

  it('defaults to three lines', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstElementChild?.children).toHaveLength(3);
  });
});
