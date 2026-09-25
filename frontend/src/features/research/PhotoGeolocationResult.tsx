import type { ResearchGeolocation } from '@/lib/api/researchGeolocation';
import { formatUtc } from '@/lib/format';

function ClueList({ title, items }: { title: string; items: readonly string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="min-w-0">
      <h4 className="text-xs font-semibold text-text">{title}</h4>
      <ul className="mt-2 list-disc space-y-1.5 pl-4 text-sm leading-relaxed text-muted">
        {items.map((item, index) => (
          <li key={index} className="break-words">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

const SUN_STATUS: Record<string, string> = {
  consistent: 'Consistent with the sun',
  inconsistent: 'Inconsistent with the sun',
  sun_below_horizon: 'Sun below the horizon',
  no_coordinates: 'No coordinates to check',
};

/** The sun and shadow arithmetic for one candidate, when a capture time was given. */
function SunChecks({ checks }: { checks: ResearchGeolocation['sun_checks'] }) {
  if (!checks || checks.length === 0) return null;
  return (
    <ul aria-label="Sun and shadow checks" className="mt-4 space-y-2">
      {checks.map((check, index) => (
        <li
          key={index}
          data-status={check.status}
          className="border-l-2 border-line pl-3 text-xs leading-relaxed data-[status=consistent]:border-chart-3 data-[status=inconsistent]:border-chart-2 data-[status=sun_below_horizon]:border-chart-2"
        >
          <p className="font-medium text-text">
            {SUN_STATUS[check.status] ?? check.status}
            <span className="ml-2 font-mono text-2xs text-muted">
              {check.photo_id.replace('photo-', 'Photo ')} · {formatUtc(check.captured_at)}
            </span>
          </p>
          <p className="mt-1 text-muted">{check.note}</p>
        </li>
      ))}
    </ul>
  );
}

/** Candidates are hypotheses, including any returned coordinates or metadata claims. */
export function PhotoGeolocationResult({ result }: { result: ResearchGeolocation }) {
  return (
    <section
      aria-label="Photo geolocation result"
      className="min-w-0 space-y-6 border-t border-line pt-6"
    >
      <header>
        <p className="text-xs font-medium uppercase tracking-widest text-ember">
          Visual assessment
        </p>
        <h3 className="mt-2 text-xl font-semibold tracking-tight">
          {result.status === 'unknown'
            ? 'No location identified'
            : 'Unverified location candidates'}
        </h3>
        <p className="mt-2 break-words text-sm leading-relaxed text-muted">{result.summary}</p>
      </header>
      {result.cross_photo_analysis && (
        <div className="border-l-2 border-ember pl-4">
          <h4 className="text-sm font-semibold">How the photos fit together</h4>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-muted">
            {result.cross_photo_analysis}
          </p>
        </div>
      )}
      <ClueList title="Visible clues" items={result.visual_clues} />
      {!!result.photos?.length && (
        <div className="divide-y divide-line border-y border-line">
          {result.photos.map((photo) => (
            <details key={photo.photo_id} className="py-3">
              <summary className="cursor-pointer text-sm font-medium">
                Photo {photo.photo_id.replace('photo-', '')}: visual evidence
              </summary>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <ClueList title="What is visible" items={photo.visual_clues} />
                <ClueList title="What remains uncertain" items={photo.limitations} />
              </div>
            </details>
          ))}
        </div>
      )}
      {result.candidates.length > 0 && (
        <ol className="divide-y divide-line border-y border-line">
          {result.candidates.map((candidate, index) => (
            <li key={index} className="py-5">
              <div className="flex items-baseline gap-3">
                <span className="font-mono text-xs text-muted">0{index + 1}</span>
                <div className="min-w-0">
                  <h4 className="break-words text-base font-semibold">{candidate.label}</h4>
                  <p className="mt-1 text-xs text-muted">
                    {candidate.precision} level
                    {candidate.country_iso ? ` · ${candidate.country_iso}` : ''} · Not verified
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <ClueList title="Supporting clues" items={candidate.supporting_clues} />
                <ClueList
                  title="Contradictions or missing evidence"
                  items={candidate.contradictions}
                />
              </div>
              {candidate.coordinates && (
                <div className="mt-4 border-l-2 border-ember/50 pl-3">
                  <p className="text-xs font-medium">Candidate position, not a verified pin</p>
                  <p className="mt-1 font-mono text-xs tabular-nums">
                    {candidate.coordinates.latitude.toFixed(4)},{' '}
                    {candidate.coordinates.longitude.toFixed(4)}
                    {' · '}uncertainty radius{' '}
                    {candidate.coordinates.uncertainty_radius_km.toLocaleString()} km
                  </p>
                  <p className="mt-1 break-words text-xs leading-relaxed text-muted">
                    {candidate.coordinates.basis}
                  </p>
                </div>
              )}
              <SunChecks
                checks={(result.sun_checks ?? []).filter(
                  (check) => check.candidate_label === candidate.label,
                )}
              />
            </li>
          ))}
        </ol>
      )}
      <ClueList title="How to verify" items={result.verification_steps} />
      <ClueList title="Limits of this assessment" items={result.limitations} />
      <details className="text-xs text-muted">
        <summary className="cursor-pointer py-2 font-medium text-text">Analysis record</summary>
        <dl className="mt-2 space-y-2 break-words">
          <div>
            <dt className="inline">Model: </dt>
            <dd className="inline">{result.provenance.returned_model}</dd>
          </div>
          <div>
            <dt className="inline">Configured model: </dt>
            <dd className="inline">{result.provenance.configured_model}</dd>
          </div>
          <div>
            <dt className="inline">Provider: </dt>
            <dd className="inline">{result.provenance.provider}</dd>
          </div>
          <div>
            <dt className="inline">Analysed: </dt>
            <dd className="inline">{formatUtc(result.provenance.analysed_at)}</dd>
          </div>
          <div>
            <dt>Original file SHA-256</dt>
            <dd className="mt-1 break-all font-mono">{result.provenance.original_sha256}</dd>
          </div>
          <div>
            <dt>Analysed preview SHA-256</dt>
            <dd className="mt-1 break-all font-mono">{result.provenance.image_sha256}</dd>
          </div>
          {result.provenance.photos?.map((photo) => (
            <div key={photo.photo_id}>
              <dt>
                Photo {photo.photo_id.replace('photo-', '')} original / analysed preview SHA-256
              </dt>
              <dd className="mt-1 break-all font-mono">
                {photo.original_sha256}
                <br />
                {photo.image_sha256}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}
