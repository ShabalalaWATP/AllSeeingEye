/**
 * Every keyboard shortcut the workspace offers, for the shortcut help. Single-key entries
 * are the ones the "Single-key shortcuts" preference turns off; the rest need a modifier,
 * are not character keys, or only work while their control has focus (WCAG 2.1.4).
 */

export interface ShortcutEntry {
  /** Alternative key presses, any of which performs the action. */
  keys: readonly string[];
  action: string;
  singleKey?: boolean;
}

export interface ShortcutGroup {
  title: string;
  entries: readonly ShortcutEntry[];
}

export const SHORTCUT_GROUPS: readonly ShortcutGroup[] = [
  {
    title: 'Anywhere in the workspace',
    entries: [
      { keys: ['Ctrl K', '⌘ K'], action: 'Find anything' },
      { keys: ['G'], action: 'Show the 3D globe', singleKey: true },
      { keys: ['M'], action: 'Show the flat map', singleKey: true },
      { keys: ['O'], action: 'Open the ops room wall screen', singleKey: true },
      { keys: ['['], action: 'Collapse or expand the navigation rail', singleKey: true },
      { keys: ['?'], action: 'Show these keyboard shortcuts', singleKey: true },
      { keys: ['Esc'], action: 'Leave the ops room, or close a dialog, panel or inspector' },
    ],
  },
  {
    title: 'On the map',
    entries: [
      { keys: ['Enter', 'Esc'], action: 'Stop placing measurement points' },
      { keys: ['Backspace'], action: 'Remove the last measurement point' },
      { keys: ['Esc'], action: 'Cancel drawing or radio station placement' },
    ],
  },
  {
    title: 'Ukraine timeline, while it has focus',
    entries: [
      { keys: ['→', '↓'], action: 'Next point on the timeline' },
      { keys: ['←', '↑'], action: 'Previous point on the timeline' },
      { keys: ['Page Down', 'Page Up'], action: 'Move four points forward or back' },
      { keys: ['Home', 'End'], action: 'First or last point' },
    ],
  },
];
