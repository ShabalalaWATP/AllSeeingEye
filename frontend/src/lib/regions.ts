/**
 * The world regions a subscription or research question can name instead of listing
 * countries. The values are the backend's own, so a saved choice survives a reload.
 */
import { z } from 'zod';
import type { components } from './api/types.gen';

export type Region = components['schemas']['Region'];

export const regionSchema = z.enum([
  'africa',
  'asia',
  'europe',
  'middle_east',
  'north_america',
  'south_america',
  'oceania',
  'antarctica',
]);

export const REGIONS: readonly { value: Region; label: string; hint: string }[] = [
  { value: 'europe', label: 'Europe', hint: 'Including Russia, Ukraine and the Caucasus' },
  { value: 'middle_east', label: 'Middle East', hint: 'From Egypt and Turkey to Iran and Yemen' },
  { value: 'africa', label: 'Africa', hint: 'The whole continent' },
  { value: 'asia', label: 'Asia', hint: 'From the Gulf to Japan and Indonesia' },
  {
    value: 'north_america',
    label: 'North America',
    hint: 'Including Central America and the Caribbean',
  },
  { value: 'south_america', label: 'South America', hint: 'The whole continent' },
  { value: 'oceania', label: 'Oceania', hint: 'Australia, New Zealand and the Pacific' },
];

export const MAX_REGIONS = 8;

export function regionLabel(value: string): string {
  return REGIONS.find((region) => region.value === value)?.label ?? value;
}
