import type { RfTerrainProfile } from '@/lib/map/rfTerrainTypes';
import { RF_STATUS_CSS } from '@/lib/map/rfTerrainPresentation';

const metric = (value: number | null | undefined, unit: string) =>
  value == null ? 'Unknown' : `${value.toFixed(1)} ${unit}`;

export function RfTerrainBudget({ profile }: { profile: RfTerrainProfile }) {
  const reserveDb = profile.reserveDb ?? 0;
  const planningMarginDb =
    profile.planningMarginDb === undefined
      ? profile.marginDb === null
        ? null
        : profile.marginDb - reserveDb
      : profile.planningMarginDb;
  return (
    <div className="space-y-3">
      <dl className="rf-result-metrics grid grid-cols-2 gap-3 text-xs">
        <div className="rf-result-metric">
          <dt className="text-muted">Modelled receive power</dt>
          <dd className="font-mono text-lg">{metric(profile.receivedDbm, 'dBm')}</dd>
        </div>
        <div className="rf-result-metric">
          <dt className="text-muted">Sampled diffraction loss</dt>
          <dd className="font-mono text-lg">{metric(profile.diffractionLossDb, 'dB')}</dd>
        </div>
        <div className="rf-result-metric">
          <dt className="text-muted">Margin above sensitivity</dt>
          <dd className="font-mono text-lg">{metric(profile.marginDb, 'dB')}</dd>
        </div>
        <div className="rf-result-metric">
          <dt className="text-muted">Margin after planning reserve</dt>
          <dd
            className="font-mono text-lg"
            style={{
              color:
                planningMarginDb === null
                  ? RF_STATUS_CSS.unknown
                  : planningMarginDb < 0
                    ? RF_STATUS_CSS.risk
                    : RF_STATUS_CSS.clear,
            }}
          >
            {metric(planningMarginDb, 'dB')}
          </dd>
        </div>
      </dl>
      <p className="text-xs text-muted">
        {reserveDb.toFixed(1)} dB planning reserve. This allowance changes the pass threshold, not
        predicted receive power. It is not a reliability percentage.
      </p>
    </div>
  );
}
