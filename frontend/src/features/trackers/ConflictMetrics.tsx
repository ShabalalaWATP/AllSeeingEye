import type { ConflictCard } from '@/lib/api/trackers';
import { ActivityCells } from './TrackerParts';

export function ConflictMetrics({ card }: { card: ConflictCard }) {
  const lower = card.fatalities_7d;
  const upper = card.fatalities_upper_7d;
  const deaths =
    lower === null
      ? null
      : upper !== null && upper > lower
        ? `${lower}\u2013${upper}`
        : String(lower);
  return (
    <div className="space-y-1 text-xs">
      <div className="font-medium text-text">Reported violence</div>
      <ActivityCells activity={card.activity} />
      <div className="font-mono text-critical">
        {deaths === null ? 'Reported deaths unknown / 7 d' : `${deaths} reported deaths / 7 d`}
      </div>
      {card.fatalities_unknown_incidents > 0 && (
        <div className="text-muted">
          {card.fatalities_unknown_incidents} incidents with unknown death counts
        </div>
      )}
      {card.fatalities_disputed_incidents > 0 && (
        <div className="text-muted">
          {card.fatalities_disputed_incidents} incidents with disputed death counts
        </div>
      )}
      <div className="text-muted">
        {card.other_activity_7d} other activity reports / 7 d, including protests
      </div>
      {card.unknown_date_reports > 0 && (
        <div className="text-muted">
          {card.unknown_date_reports} reports with unknown or imprecise occurrence dates
        </div>
      )}
      {card.collapsed_reports_7d > 0 && (
        <div className="text-muted">
          {card.collapsed_reports_7d} duplicate or linked reports collapsed / 7 d
        </div>
      )}
    </div>
  );
}

export function ConflictCoverageNote() {
  return (
    <p className="text-xs leading-relaxed text-muted">
      Counts reflect bounded retained coverage, by reported occurrence date. Death counts sum known
      reports, not the whole-conflict toll. No reports collected does not establish absence.
      Protests and other activity are separate from reported violence; grouped reports do not
      establish independent verification.
    </p>
  );
}
