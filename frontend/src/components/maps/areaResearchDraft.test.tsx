import { act, fireEvent, screen } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { mountAreaPanel, researchArea } from '@/test/areaResearchPanel';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { prepareAreaResearchHandoff, readAreaResearchHandoff } from '@/lib/areaResearchDraft';

beforeEach(() => applySession('user'));

it('preserves the question and settings after the tool closes without preserving disclosure consent', () => {
  const first = mountAreaPanel();
  fireEvent.change(screen.getByLabelText('Question (optional)'), {
    target: { value: 'Harbour activity?' },
  });
  fireEvent.change(screen.getByLabelText('Research period'), { target: { value: '7' } });
  fireEvent.change(screen.getByLabelText('Research depth'), { target: { value: 'quick' } });
  first.unmount();
  mountAreaPanel();
  expect(screen.getByLabelText('Question (optional)')).toHaveValue('Harbour activity?');
  expect(screen.getByLabelText('Research period')).toHaveValue('7');
  expect(screen.getByLabelText('Research depth')).toHaveValue('quick');
  expect(screen.getByRole('checkbox', { name: /Allow research providers/ })).not.toBeChecked();
});

it.each(['logout', 'workspace'] as const)(
  'does not revive a private draft after %s while the tool is closed',
  (cause) => {
    const first = mountAreaPanel();
    fireEvent.change(screen.getByLabelText('Question (optional)'), {
      target: { value: 'Private question' },
    });
    first.unmount();
    act(() => {
      if (cause === 'logout') {
        applySession('anonymous');
        applySession('user');
      } else invalidateWorkspaceAccess();
    });
    mountAreaPanel();
    expect(screen.getByLabelText('Question (optional)')).toHaveValue('');
  },
);

it('copies exact geometry for an in-memory handoff and discards it on authority change', () => {
  const geometry = structuredClone(researchArea);
  prepareAreaResearchHandoff(geometry);
  geometry.features.splice(0);
  expect(readAreaResearchHandoff()?.area).toEqual(researchArea);
  act(() => invalidateWorkspaceAccess());
  expect(readAreaResearchHandoff()).toBeNull();
});

it('rejects invalid geometry, time windows and anonymous handoffs', () => {
  expect(() =>
    prepareAreaResearchHandoff(researchArea, { since: 'invalid', until: 'invalid' }),
  ).toThrow(/interval/);
  expect(() => prepareAreaResearchHandoff({ type: 'FeatureCollection', features: [] })).toThrow();
  act(() => applySession('anonymous'));
  expect(() => prepareAreaResearchHandoff(researchArea)).toThrow(/Sign in/);
  expect(readAreaResearchHandoff()).toBeNull();
});
