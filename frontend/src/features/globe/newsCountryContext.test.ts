import { expect, it } from 'vitest';
import { countries, liveEvent } from '@/test/fixtures';
import { newsCountryGroups } from './useNewsCountryContext';

const directory = Object.fromEntries(countries.map((country) => [country.iso2, country]));
it('never guesses location from a headline, publisher, invalid centroid or unrelated category', () => {
  const event = liveEvent({
    category: 'news',
    country_iso: 'GB',
    geo_confidence: 'country',
    point: null,
  });
  expect(newsCountryGroups([event], directory)[0]?.events).toEqual([event]);
  expect(event.point).toBeNull();
  expect(
    newsCountryGroups(
      [
        {
          ...event,
          country_iso: null,
          title: 'United Kingdom and China',
          attributes: { publisher_country: 'GB' },
        },
        { ...event, geo_confidence: 'none' },
        { ...event, category: 'cyber' },
        { ...event, country_iso: 'XX' },
      ],
      directory,
    ),
  ).toEqual([]);
  expect(newsCountryGroups([event], { GB: { ...directory.GB!, centroid: [NaN, 54] } })).toEqual([]);
  expect(newsCountryGroups([event], { GB: { ...directory.GB!, centroid: [0, 91] } })).toEqual([]);
});
