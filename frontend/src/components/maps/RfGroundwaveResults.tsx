import type { RfAnalysis } from '@/lib/map/rfAnalysis';
import { hfGroundwaveReceiver, hfGroundwaveSummary } from '@/lib/map/hfGroundwaveMap';
import { measure } from '@/lib/map/measurements';

type GroundwaveAnalysis = Extract<RfAnalysis, { kind: 'hf-groundwave' }>;
const km = (distance: number) => distance.toLocaleString('en-GB', { maximumFractionDigits: 1 });

/** A sampled model curve, not an interpolated claim of a maximum service range. */
export function RfGroundwaveResults({ analysis }: { analysis: GroundwaveAnalysis }) {
  const { result, input, origin, receiver } = analysis;
  const reserveDb = analysis.engineering?.reserveDb ?? 0;
  const thresholdDbm = input.sensitivityDbm + reserveDb;
  const summary = hfGroundwaveSummary(result, input.sensitivityDbm, reserveDb);
  const receiverDistance = receiver ? measure([origin, receiver], 'distance').metres / 1000 : null;
  const receive = receiverDistance === null ? null : hfGroundwaveReceiver(result, receiverDistance);
  const powers = result.samples.map((sample) => sample.received_power_dbm);
  const top = Math.max(...powers, thresholdDbm) + 6;
  const bottom = Math.min(...powers, input.sensitivityDbm) - 6;
  const x = (distance: number) =>
    40 +
    (258 * Math.log(distance / summary.checkedFromKm)) /
      Math.log(summary.checkedToKm / summary.checkedFromKm);
  const y = (power: number) => 20 + (106 * (top - power)) / (top - bottom);
  const thresholdY = y(thresholdDbm);
  const curve = result.samples
    .map(
      (sample) => `${x(sample.distance_km).toFixed(2)},${y(sample.received_power_dbm).toFixed(2)}`,
    )
    .join(' ');
  const status = summary.noPassing
    ? 'No passing range established'
    : summary.atLimit
      ? 'Passes through sampled limit'
      : 'Last consecutive passing sample';
  return (
    <section aria-label="HF groundwave model results" className="space-y-3 text-xs">
      <div className="rf-result-summary space-y-3">
        <p className="rf-result-kicker font-mono uppercase tracking-wider text-muted">{status}</p>
        <p
          className={`mt-1 font-mono text-xl ${summary.noPassing ? 'text-amber-300' : 'text-cyan'}`}
        >
          {summary.radiusKm === null ? 'Below threshold' : `${km(summary.radiusKm)} km`}
        </p>
        <p className="mt-2 text-muted">
          {summary.noPassing
            ? `The first model sample at ${km(summary.checkedFromKm)} km is below the planning threshold. No closer range was calculated.`
            : summary.atLimit
              ? `Every checked sample meets the planning threshold through ${km(summary.checkedToKm)} km. This is the search limit, not a maximum range.`
              : `The next checked sample at ${km(summary.firstFailureKm ?? summary.checkedToKm)} km is below the planning threshold. The threshold crossing between samples is unresolved.`}
        </p>
        <p className="text-muted">
          Threshold {thresholdDbm.toFixed(1)} dBm = sensitivity {input.sensitivityDbm.toFixed(1)}{' '}
          dBm + {reserveDb.toFixed(1)} dB planning reserve.
        </p>
        {summary.noPassing && (
          <p className="rf-result-next-step text-amber-200">
            Check the equipment sensitivity, antenna gains and ground conductivity. The model begins
            at 1 km; it cannot determine shorter-range reception.
          </p>
        )}
      </div>
      <p className="text-muted">
        {result.samples.length} samples from {km(summary.checkedFromKm)} to{' '}
        {km(summary.checkedToKm)} km. Nothing closer than or beyond this interval is inferred. Later
        isolated passing samples do not extend the range outline.
      </p>
      <figure className="rf-profile rounded border border-line bg-ground/60 p-2">
        <svg
          viewBox="0 0 320 160"
          className="w-full"
          role="img"
          aria-label="Modelled received power versus distance"
        >
          <title>HF groundwave model power curve</title>
          <desc>
            Cyan line shows sampled received power. Amber dashed line shows sensitivity plus the
            planning reserve. The grey dotted line shows sensitivity alone when reserve is applied.
            Distance uses a logarithmic scale. This is model output, not a measurement.
          </desc>
          <line x1="40" y1="20" x2="40" y2="126" stroke="currentColor" className="text-muted/40" />
          <line
            x1="40"
            y1="126"
            x2="298"
            y2="126"
            stroke="currentColor"
            className="text-muted/40"
          />
          <line
            data-power-threshold="planning"
            x1="40"
            y1={thresholdY}
            x2="298"
            y2={thresholdY}
            stroke="currentColor"
            strokeDasharray="4 4"
            className="text-amber-300"
          />
          {reserveDb > 0 && (
            <line
              data-power-threshold="sensitivity"
              x1="40"
              y1={y(input.sensitivityDbm)}
              x2="298"
              y2={y(input.sensitivityDbm)}
              stroke="#9aa7bc"
              strokeDasharray="1 4"
            />
          )}
          <polyline
            points={curve}
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-cyan"
          />
          {result.samples.map((sample) => (
            <circle
              key={sample.distance_km}
              cx={x(sample.distance_km)}
              cy={y(sample.received_power_dbm)}
              r="1.7"
              fill="currentColor"
              className="text-cyan"
            />
          ))}
          {receive && (
            <circle
              cx={x(receive.distanceKm)}
              cy={y(receive.receivedDbm)}
              r="4"
              fill="currentColor"
              className="text-amber-200"
              stroke="#080c10"
              strokeWidth="1.5"
            />
          )}
          <text
            x="34"
            y="23"
            textAnchor="end"
            fill="currentColor"
            fontSize="9"
            className="text-muted"
          >
            {top.toFixed(0)}
          </text>
          <text
            x="34"
            y="127"
            textAnchor="end"
            fill="currentColor"
            fontSize="9"
            className="text-muted"
          >
            {bottom.toFixed(0)}
          </text>
          <text
            x="40"
            y="141"
            textAnchor="start"
            fill="currentColor"
            fontSize="9"
            className="text-muted"
          >
            {km(summary.checkedFromKm)} km
          </text>
          <text
            x="298"
            y="141"
            textAnchor="end"
            fill="currentColor"
            fontSize="9"
            className="text-muted"
          >
            {km(summary.checkedToKm)} km
          </text>
          <text x="40" y="11" fill="currentColor" fontSize="9" className="text-muted">
            Received power (dBm)
          </text>
          <text
            x="169"
            y="155"
            textAnchor="middle"
            fill="currentColor"
            fontSize="9"
            className="text-muted"
          >
            Distance · logarithmic scale
          </text>
        </svg>
        <figcaption className="flex flex-wrap justify-between gap-2 px-2 text-muted">
          <span className="text-cyan">Model samples</span>
          <span className="text-amber-300">Planning threshold {thresholdDbm.toFixed(1)} dBm</span>
          <span className="text-muted">Sensitivity {input.sensitivityDbm.toFixed(1)} dBm</span>
        </figcaption>
      </figure>
      {receiverDistance !== null && (
        <div className="border-y border-line py-3">
          <p className="font-mono uppercase tracking-wide text-muted">
            Receiver · {km(receiverDistance)} km
          </p>
          {receive ? (
            <>
              <dl className="rf-result-metrics mt-2 grid grid-cols-2 gap-2">
                <div className="rf-result-metric">
                  <dt className="text-muted">Modelled receive level</dt>
                  <dd className="mt-1 font-mono text-base text-text">
                    {receive.receivedDbm.toFixed(1)} dBm
                  </dd>
                </div>
                <div className="rf-result-metric">
                  <dt className="text-muted">Margin above sensitivity</dt>
                  <dd
                    className={`mt-1 font-mono text-base ${receive.receivedDbm < input.sensitivityDbm ? 'text-amber-300' : 'text-cyan'}`}
                  >
                    {(receive.receivedDbm - input.sensitivityDbm).toFixed(1)} dB
                  </dd>
                </div>
                <div className="rf-result-metric">
                  <dt className="text-muted">Margin after planning reserve</dt>
                  <dd
                    className={`mt-1 font-mono text-base ${receive.receivedDbm < thresholdDbm ? 'text-amber-300' : 'text-cyan'}`}
                  >
                    {(receive.receivedDbm - thresholdDbm).toFixed(1)} dB
                  </dd>
                </div>
              </dl>
              <p className="mt-2 text-muted">
                {receive.interpolated
                  ? 'Interpolated between model samples using logarithmic distance.'
                  : 'At a calculated model sample.'}{' '}
                This does not establish a usable link or account for radio noise.
              </p>
            </>
          ) : (
            <p className="mt-2 text-amber-300">
              Receiver is outside the sampled interval. No received level or link margin is
              estimated.
            </p>
          )}
        </div>
      )}
      <p className="text-muted">
        Smooth, homogeneous ground scenario. Terrain, buildings, vegetation and skywave are
        excluded. The cyan outline is the last consecutive passing sample; amber marks the first
        failed sample. The selected reserve is an allowance, not modelled noise, fading or a
        reliability percentage. It does not change predicted receive power.
      </p>
      <details className="rounded border border-line p-3">
        <summary className="cursor-pointer text-text">Model, source and sample values</summary>
        <p className="mt-3 text-muted">{result.model}</p>
        <p className="mt-2 text-muted">{result.limitations}</p>
        <a
          href={result.source_url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-block text-cyan underline"
        >
          NTIA LFMF source and model documentation
        </a>
        <div className="mt-3 max-h-48 overflow-auto">
          <table className="w-full text-right font-mono">
            <caption className="sr-only">Groundwave samples and receiver threshold margin</caption>
            <thead className="text-muted">
              <tr>
                <th className="p-1 font-normal">km</th>
                <th className="p-1 font-normal">dBm</th>
                <th className="p-1 font-normal">Raw margin dB</th>
                <th className="p-1 font-normal">After reserve dB</th>
              </tr>
            </thead>
            <tbody>
              {result.samples.map((sample) => (
                <tr key={sample.distance_km} className="border-t border-line">
                  <td className="p-1">{km(sample.distance_km)}</td>
                  <td className="p-1">{sample.received_power_dbm.toFixed(1)}</td>
                  <td className="p-1">
                    {(sample.received_power_dbm - input.sensitivityDbm).toFixed(1)}
                  </td>
                  <td className="p-1">{(sample.received_power_dbm - thresholdDbm).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
