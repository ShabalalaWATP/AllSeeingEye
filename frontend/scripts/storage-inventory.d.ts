export interface DeclarationRow {
  name: string;
  kind: string;
}
export function storageProblems(root: string, declarations: readonly DeclarationRow[]): string[];
export function browserStorageKeys(
  source: string,
  filename?: string,
  forwardingAdapter?: boolean,
): { keys: string[]; failures: string[] };
export function cookieKeys(source: string): string[];
