import { expect, it, vi } from 'vitest';
import { isObservationShown, toggleObservationLayer } from './layerVisibility';

it.each(['aircraft', 'vessels', 'firms'] as const)(
  'restores %s and its hidden parent from either saved state',
  (kind) => {
    for (const saved of [true, false]) {
      const visibility = { aircraft: saved, vessels: saved, firms: saved };
      const hidden = ['aviation', 'maritime', 'disaster'] as const;
      const observation = vi.fn();
      const category = vi.fn();
      expect(isObservationShown(kind, visibility, hidden)).toBe(false);
      toggleObservationLayer(kind, visibility, hidden, observation, category);
      expect(category).toHaveBeenCalledExactlyOnceWith(
        { aircraft: 'aviation', vessels: 'maritime', firms: 'disaster' }[kind],
      );
      expect(observation).toHaveBeenCalledTimes(saved ? 0 : 1);
      if (!saved) expect(observation).toHaveBeenCalledWith(kind);
    }
  },
);

it('changes only the subgroup when the parent is already shown', () => {
  const visibility = { aircraft: true, vessels: false, firms: true };
  const observation = vi.fn();
  const category = vi.fn();
  expect(isObservationShown('aircraft', visibility, [])).toBe(true);
  expect(isObservationShown('vessels', visibility, [])).toBe(false);
  toggleObservationLayer('vessels', visibility, [], observation, category);
  expect(observation).toHaveBeenCalledExactlyOnceWith('vessels');
  expect(category).not.toHaveBeenCalled();
});
