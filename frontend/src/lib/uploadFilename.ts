/** The server accepts research upload filenames of at most this many characters. */
export const MAX_INPUT_FILENAME_LENGTH = 120;

/** Why a filename would be refused, checked before any bytes are sent. */
export function inputFilenameError(name: string): string | null {
  // Count code points, as the server does, rather than UTF-16 units.
  return Array.from(name).length > MAX_INPUT_FILENAME_LENGTH
    ? `Rename the file to ${String(MAX_INPUT_FILENAME_LENGTH)} characters or fewer, then choose it again.`
    : null;
}
