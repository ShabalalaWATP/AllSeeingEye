/** Save a binary response, releasing its temporary object URL even if the browser fails. */
export function saveBinaryFile(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  try {
    anchor.href = url;
    anchor.download = name;
    anchor.rel = 'noopener';
    document.body.append(anchor);
    anchor.click();
  } finally {
    anchor.remove();
    URL.revokeObjectURL(url);
  }
}
