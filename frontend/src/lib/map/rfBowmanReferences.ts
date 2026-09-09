/** Public evidence only. Frequencies below are illustrative choices, not network settings. */
export const BOWMAN_REFERENCES = [
  {
    title: 'Cooper Antennas: Bowman VHF band',
    url: 'https://www.cooperantennas.com/airborne-antennas.php',
    detail:
      'Manufacturer lists Bowman-compatible antennas covering 30–88 MHz. This documents a supported band, not radio output power or operational frequencies.',
  },
  {
    title: 'UK Parliament: PRC325 HF manpack',
    url: 'https://hansard.parliament.uk/Commons/2005-03-02/debates/a9d8af13-2718-4f0c-86c0-bbf5e3f9f31f/BowmanSystem',
    detail:
      'Ministerial answer identifies the Bowman PRC325 HF manpack. It does not publish power settings or a variant datasheet.',
  },
  {
    title: 'General Dynamics: Bowman radio families',
    url: 'https://gdmissionsystems.com/articles/2015/09/15/news-release-general-dynamics-shows-its-strength-at-dsei-2015',
    detail:
      'Manufacturer describes a Bowman installation supporting HF, VHF and UHF voice and data. No verified variant power table is provided.',
  },
] as const;
