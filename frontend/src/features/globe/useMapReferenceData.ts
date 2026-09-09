import { useCallback, useEffect } from 'react';
import { useCapabilitiesStore } from '@/stores/capabilities';
import { useCountriesStore } from '@/stores/countries';
import type { BaseLayer } from '@/stores/globe';
import { isOsLayer } from './engine/baseLayers';

/** Load reference catalogues and reject a remembered map style unavailable on this server. */
export function useMapReferenceData(
  baseLayer: BaseLayer,
  setBaseLayer: (layer: BaseLayer) => void,
) {
  const osMaps = useCapabilitiesStore((state) => state.osMaps);
  const loaded = useCapabilitiesStore((state) => state.loaded);
  const osLoading = useCapabilitiesStore((state) => state.loading);
  const osError = useCapabilitiesStore((state) => state.error);
  const loadCapabilities = useCapabilitiesStore((state) => state.load);
  const recheckOs = useCallback(() => {
    void loadCapabilities(true);
  }, [loadCapabilities]);
  const countries = useCountriesStore((state) => state.items);
  const countryByIso = useCountriesStore((state) => state.byIso);
  const countriesError = useCountriesStore((state) => state.error);
  const loadCountries = useCountriesStore((state) => state.load);
  useEffect(() => {
    void loadCapabilities();
  }, [loadCapabilities]);
  useEffect(() => {
    void loadCountries();
  }, [loadCountries]);
  useEffect(() => {
    if (loaded && !osLoading && !osError && !osMaps && isOsLayer(baseLayer)) setBaseLayer('dark');
  }, [baseLayer, loaded, osLoading, osError, osMaps, setBaseLayer]);
  return { osMaps, osLoading, osError, recheckOs, countries, countryByIso, countriesError };
}
