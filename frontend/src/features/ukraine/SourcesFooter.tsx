import type { ControlSummary } from '@/lib/api/ukraine';

const SOURCES = [
  {
    name: 'ISW Russian Offensive Campaign Assessments',
    role: 'Daily assessments by the Institute for the Study of War, read from its posts index.',
    terms: 'Title, link and a short excerpt under the ISW fair use and attribution policy.',
    url: 'https://www.understandingwar.org/',
  },
  {
    name: 'General Staff of the Armed Forces of Ukraine',
    role: 'Daily cumulative claims of Russian losses, through the russianwarship.rip mirror.',
    terms: 'A party to the conflict reporting its own count; shown as claims.',
    url: 'https://russianwarship.rip/',
  },
  {
    name: 'The Kyiv Independent, Ukrinform, Ukrainska Pravda',
    role: 'Ukrainian reporting from public feeds.',
    terms: 'Headlines and links only; publisher rights apply.',
    url: 'https://kyivindependent.com/',
  },
  {
    name: 'Meduza, Interfax, Russian MFA, TASS',
    role: 'Russian and independent Russian reporting; state outlets are labelled.',
    terms: 'State control is a caution, not proof that an item is false.',
    url: 'https://meduza.io/en',
  },
  {
    name: 'geoBoundaries',
    role: 'Oblast outlines, simplified once.',
    terms: 'ODbL, OpenStreetMap contributors.',
    url: 'https://www.geoboundaries.org/',
  },
] as const;

/** Attribution and the doctrine in plain words: who reported what, and what this page cannot say. */
export function SourcesFooter({ control }: { control: ControlSummary | null }) {
  return (
    <section id="sources" aria-labelledby="ukraine-sources-heading" className="flex flex-col gap-3">
      <h2 id="ukraine-sources-heading" className="text-base font-semibold">
        Sources and what this page cannot tell you
      </h2>
      <p className="max-w-3xl text-sm text-muted">
        The frontline is a reported line, not observed positions. Loss figures are the
        claimant&apos;s own. Assessments are one institute&apos;s judgement. Reporting is graded for
        source reliability, not for truth. Nothing on this page has been verified by this
        application, and no number here should be repeated without its basis.
      </p>
      <ul aria-label="Sources" className="grid gap-2 md:grid-cols-2">
        {control ? (
          <li className="rounded-card border border-line bg-surface p-3 text-sm">
            <a
              href={control.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-text hover:underline"
            >
              VIINA 2.0 territorial control
            </a>
            <p className="text-xs text-muted">{control.attribution}</p>
            <p className="text-xs text-muted">
              {control.licence}. Assessed {control.assessment_date}, release{' '}
              {control.release_stamp.slice(0, 8)}.
            </p>
          </li>
        ) : null}
        {SOURCES.map((source) => (
          <li key={source.name} className="rounded-card border border-line bg-surface p-3 text-sm">
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-text hover:underline"
            >
              {source.name}
            </a>
            <p className="text-xs text-muted">{source.role}</p>
            <p className="text-xs text-muted">{source.terms}</p>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">
        DeepStateMap, ISW control-of-terrain geodata and the UN OCHA frontline layer are not drawn:
        their terms require permission or a humanitarian purpose. The map&apos;s Conflict panel
        lists the access routes.
      </p>
    </section>
  );
}
