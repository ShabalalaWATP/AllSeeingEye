import { act, renderHook } from '@testing-library/react';
import { expect, it } from 'vitest';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useInfrastructure } from './useInfrastructure';

it('cannot enable bundled military reference records while their policy is denied', () => {
  useCapabilitiesStore.setState({ loaded: true, commercialUse: true, sourceLicences: {} });
  const { result } = renderHook(() => useInfrastructure());
  act(() => result.current.toggleMilitary());
  expect(result.current.militaryEnabled).toBe(false);
  expect(result.current.militaryCountries).toEqual([]);
  act(() => result.current.enableTechnology());
  expect(result.current.stationsEnabled).toBe(false);
  expect(result.current.cablesEnabled).toBe(false);
});
