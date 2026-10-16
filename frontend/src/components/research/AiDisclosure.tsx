const COPY = {
  assessment: [
    'AI-assisted assessment',
    'It may contain errors. Check original sources and important details before relying on it.',
  ],
  translation: [
    'AI-assisted translation',
    'Meaning is unverified. Check the original text before relying on it.',
  ],
  assistant: [
    'AI assistant',
    'Responses may contain errors. Check the cited sources before relying on them.',
  ],
  explanation: [
    'AI-assisted explanation',
    'Check the figures and their dates before relying on this explanation.',
  ],
} as const;

/** Presentation only: stays visible independently of provider readiness or review status. */
export function AiDisclosure({
  kind = 'assessment',
  compact = false,
  className = 'text-xs leading-5 text-muted',
}: {
  kind?: keyof typeof COPY;
  compact?: boolean;
  className?: string | undefined;
}) {
  const [label, detail] = COPY[kind];
  const Element = compact ? 'span' : 'p';
  return (
    <Element className={className}>
      <span className="font-medium">{label}</span>
      {!compact && <>. {detail}</>}
    </Element>
  );
}
