/**
 * An SVG path that draws itself as its chapter's --progress rises. The stroke is
 * normalised with pathLength, so drawing is a stroke-dashoffset change only; a still
 * story shows the whole line. Place inside an aria-hidden SVG.
 */
import type { CSSProperties, SVGProps } from 'react';

import '../story-motion.css';

export interface DrawPathProps extends Omit<SVGProps<SVGPathElement>, 'pathLength'> {
  d: string;
  /** Chapter progress (0..1) at which the line starts drawing. */
  start?: number;
  /** How fast the line draws: 1 takes the whole chapter, 4 a quarter of it. */
  rate?: number;
}

export function DrawPath({ start = 0, rate = 1, className = '', style, ...path }: DrawPathProps) {
  const timing = { '--draw-start': start, '--draw-rate': rate, ...style } as CSSProperties;
  return <path {...path} pathLength={1} className={`draw-path ${className}`} style={timing} />;
}
