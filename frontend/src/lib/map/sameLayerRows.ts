/** Immutable row identity preserves Deck attributes when only callbacks/styles change. */
export function sameLayerRows(left: unknown, right: unknown): boolean {
  if (left === right) return true;
  if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
  return left.every((row: unknown, index: number) => row === right[index]);
}
