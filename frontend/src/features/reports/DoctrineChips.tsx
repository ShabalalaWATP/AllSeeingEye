import { probabilityTerm } from '@/lib/doctrine';
import { bandText } from '@/lib/hooks/useYardstick';
import type { Yardstick } from '@/lib/hooks/useYardstick';

import { confidenceTone, yardstickPosition, type Tone } from './doctrineTone';

/**
 * Labelled chips for recorded doctrine values. Every chip shows its label and its
 * value as text; the tone only repeats what the words already say.
 */
export function Chip({
  label,
  value,
  tone = 'neutral',
  children,
}: {
  label: string;
  value: string;
  tone?: Tone;
  children?: React.ReactNode;
}) {
  return (
    <span className="report-reader-fact" data-tone={tone}>
      <span className="report-reader-fact-label">{label}</span>
      <span>{value}</span>
      {children}
    </span>
  );
}

/**
 * The UK PHIA yardstick term, its configured band as readable text, and its position on the
 * seven-band scale. The band comes from the server's yardstick; an unknown term or an
 * unavailable yardstick is said plainly rather than given a guessed range.
 */
export function LikelihoodChip({
  probability,
  yardstick = null,
}: {
  probability: string;
  yardstick?: Yardstick;
}) {
  const { band, bands } = yardstickPosition(probability);
  const range = bandText(yardstick, probability);
  return (
    <Chip label="Likelihood" value={probabilityTerm(probability)} tone="neutral">
      {range !== null && <span className="report-reader-fact-label">{range}</span>}
      {band > 0 && (
        <span className="report-reader-scale" aria-hidden="true">
          {Array.from({ length: bands }, (_, index) => (
            <span key={index} data-filled={index < band} />
          ))}
        </span>
      )}
    </Chip>
  );
}

export function ConfidenceChip({ confidence }: { confidence: string }) {
  return <Chip label="Confidence" value={confidence} tone={confidenceTone(confidence)} />;
}
