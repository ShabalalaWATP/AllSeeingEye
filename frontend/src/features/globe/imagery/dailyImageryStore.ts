/**
 * The dated imagery choice for this session. Off by default and never persisted, so a
 * reload never contacts NASA until an analyst switches the layer on again.
 */
import { create } from 'zustand';

import {
  defaultDailyImageryDate,
  validDailyImagery,
  type DailyImagery,
  type DailyImageryProductId,
} from '@/lib/map/dailyImagery';

export interface DailyImageryState {
  enabled: boolean;
  product: DailyImageryProductId;
  /** As entered; only a validated date ever reaches a tile URL. */
  date: string;
  /** Some tiles for the current choice failed; the base map stays in place. */
  failed: boolean;
  setEnabled: (enabled: boolean) => void;
  setProduct: (product: DailyImageryProductId) => void;
  setDate: (date: string) => void;
  markFailed: () => void;
  reset: () => void;
}

function initial() {
  return {
    enabled: false,
    product: 'modis_terra' as DailyImageryProductId,
    date: defaultDailyImageryDate(Date.now()),
    failed: false,
  };
}

export const useDailyImageryStore = create<DailyImageryState>()((set) => ({
  ...initial(),
  setEnabled: (enabled) => {
    set({ enabled, failed: false });
  },
  setProduct: (product) => {
    set({ product, failed: false });
  },
  setDate: (date) => {
    set({ date, failed: false });
  },
  markFailed: () => {
    set((state) => (state.enabled && !state.failed ? { failed: true } : state));
  },
  reset: () => {
    set(initial());
  },
}));

/** What the map should draw: null when off or when the entered date is not valid. */
export function selectDailyImagery(
  state: Pick<DailyImageryState, 'enabled' | 'product' | 'date'>,
  now: number = Date.now(),
): DailyImagery | null {
  return state.enabled ? validDailyImagery(state.product, state.date, now) : null;
}
