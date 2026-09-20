/** The mirror owns default selections; a view may validate its broader merged collection. */
export type SelectionOwner = 'mirror' | 'view';

export function selectionAfterMirrorUpdate(
  selection: { selectedId: string | null; selectionOwner: SelectionOwner },
  records: Readonly<Record<string, unknown>>,
): string | null {
  const { selectedId, selectionOwner } = selection;
  return selectedId !== null && selectionOwner === 'mirror' && !(selectedId in records)
    ? null
    : selectedId;
}
