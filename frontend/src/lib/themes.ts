/**
 * The themes a subscription can follow. Each one is an evidence category the collectors
 * already tag, named the way a reader would ask for it. News is not a theme: it is the
 * ground every question stands on, so leaving themes empty keeps everything.
 */
import type { Category } from './api/eventSchemas';

export const MAX_THEMES = 4;

export const THEMES: readonly { value: Category; label: string; hint: string }[] = [
  { value: 'conflict', label: 'Conflict', hint: 'Fighting, unrest and military activity' },
  { value: 'political', label: 'Politics', hint: 'Governments, elections and diplomacy' },
  { value: 'economic', label: 'Economy', hint: 'Markets, trade, sanctions and prices' },
  { value: 'cyber', label: 'Cyber', hint: 'Intrusions, outages and vulnerabilities' },
  { value: 'social', label: 'Public view', hint: 'What people are posting and sharing' },
  { value: 'disaster', label: 'Disasters', hint: 'Earthquakes, storms, floods and fires' },
  { value: 'humanitarian', label: 'Humanitarian', hint: 'Displacement, aid and public health' },
  { value: 'aviation', label: 'Aviation', hint: 'Military and unusual flying' },
  { value: 'maritime', label: 'Maritime', hint: 'Shipping, navies and sea warnings' },
  { value: 'space', label: 'Space', hint: 'Launches, satellites and space weather' },
];

export function themeLabel(value: string): string {
  return THEMES.find((theme) => theme.value === value)?.label ?? value;
}
