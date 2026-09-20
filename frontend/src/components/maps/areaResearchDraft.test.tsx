import { act, fireEvent, screen } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { applySession } from '@/test/render';
import { mountAreaPanel, researchArea } from '@/test/areaResearchPanel';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import {
  prepareAreaResearchHandoff,
  readAreaResearchHandoff,
  useAreaResearchDraft,
} from '@/lib/areaResearchDraft';
import { useAuthStore } from '@/stores/auth';

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

it('rejects oversized, overly detailed and non-area geometry before replacing a valid draft', () => {
  prepareAreaResearchHandoff(researchArea);
  const previous = readAreaResearchHandoff();
  const oversized = structuredClone(researchArea);
  oversized.features[0]!.properties = { label: 'x'.repeat(17000) };
  expect(() => prepareAreaResearchHandoff(oversized)).toThrow('16 KiB');
  const detailed = structuredClone(researchArea);
  const ring = Array.from({ length: 257 }, (_, i): [number, number] => {
    const angle = (i * 2 * Math.PI) / 257;
    return [Number(Math.cos(angle).toFixed(6)), Number(Math.sin(angle).toFixed(6))];
  });
  detailed.features[0]!.geometry = { type: 'Polygon', coordinates: [[...ring, ring[0]!]] };
  expect(() => prepareAreaResearchHandoff(detailed)).toThrow('256 vertices');
  const point = structuredClone(researchArea);
  point.features[0]!.geometry = { type: 'Point', coordinates: [0, 0] };
  expect(() => prepareAreaResearchHandoff(point)).toThrow('polygon boundary');
  expect(readAreaResearchHandoff()).toBe(previous);
});

it.each(['role', 'inactive'] as const)('clears the draft on same-account %s change', (change) => {
  prepareAreaResearchHandoff(researchArea);
  act(() => {
    const user = useAuthStore.getState().user!;
    useAuthStore.setState({
      user: change === 'role' ? { ...user, role: 'admin' } : { ...user, is_active: false },
    });
  });
  expect(readAreaResearchHandoff()).toBeNull();
  if (change === 'inactive')
    expect(() => prepareAreaResearchHandoff(researchArea)).toThrow('Sign in');
});

it('copies explicit source selection and restores automatic source choice with null', () => {
  const ids = ['research-firms'];
  useAreaResearchDraft.getState().setSourceIds(ids);
  ids.push('research-news');
  expect(useAreaResearchDraft.getState().sourceIds).toEqual(['research-firms']);
  useAreaResearchDraft.getState().setSourceIds(null);
  expect(useAreaResearchDraft.getState().sourceIds).toBeNull();
});
