/** The nations the resolver knows, loaded once for the filter and the country panel. */
import { create } from 'zustand';

import { describeError } from '@/lib/api/errors';
import { fetchCountries } from '@/lib/api/geo';
import type { Country } from '@/lib/api/geoSchemas';

export interface CountriesState {
  items: Country[];
  byIso: Record<string, Country>;
  loaded: boolean;
  error: string | null;
  load: () => Promise<void>;
}

export const initialCountriesState = {
  items: [] as Country[],
  byIso: {} as Record<string, Country>,
  loaded: false,
  error: null as string | null,
};

export const useCountriesStore = create<CountriesState>()((set, get) => ({
  ...initialCountriesState,

  load: async () => {
    if (get().loaded) return;
    try {
      const items = await fetchCountries();
      const byIso: Record<string, Country> = {};
      for (const country of items) byIso[country.iso2] = country;
      set({ items, byIso, loaded: true, error: null });
    } catch (caught) {
      // Not marked loaded, so the next mount tries again.
      set({ error: describeError(caught) });
    }
  },
}));
