import { act, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockMatchMedia, setVisibility } from '@/test/env';

import { BrandMark } from './BrandMark';
import { Wordmark } from './Wordmark';

describe('BrandMark', () => {
  it('runs the eye with a fixed pupil at 24 fps on the page ground', () => {
    render(<BrandMark />);
    const mark = screen.getByRole('img', { name: 'The All Seeing Eye' });
    expect(mark).toHaveStyle({ width: '56px', height: '40px' });
    const eye = screen.getByTestId('evil-eye');
    expect(eye).toHaveAttribute('data-pupil-follow', '0');
    expect(eye).toHaveAttribute('data-max-fps', '24');
    expect(eye).toHaveAttribute('data-flame-speed', '1');
    expect(eye).toHaveAttribute('data-paused', 'false');
    expect(eye).toHaveAttribute('data-background', '#07070b');
  });

  it('pauses while the tab is hidden and resumes when it is visible again', () => {
    setVisibility('hidden');
    render(<BrandMark size={56} />);
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-paused', 'true');
    act(() => {
      setVisibility('visible');
    });
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-paused', 'false');
  });

  it('renders a static eye under prefers-reduced-motion', () => {
    mockMatchMedia(true);
    render(<BrandMark />);
    const eye = screen.getByTestId('evil-eye');
    expect(eye).toHaveAttribute('data-flame-speed', '0');
    expect(eye).toHaveAttribute('data-max-fps', '1');
  });

  it('copes with browsers that lack matchMedia', () => {
    Reflect.deleteProperty(window, 'matchMedia');
    render(<BrandMark />);
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-max-fps', '24');
  });

  it('shows the wordmark text', () => {
    render(<Wordmark />);
    expect(screen.getByText('The All Seeing Eye')).toHaveClass('font-mono', 'uppercase');
  });
});
