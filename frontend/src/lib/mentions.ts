/**
 * Board @mentions read from plain text, matching the server's parser so the composer can
 * show the ten-teammate limit before posting. The server still resolves every handle
 * against the team's current roster; nothing here decides who is notified.
 */
export const MAX_MENTIONS = 10;

const MENTION = /(?<![A-Za-z0-9_@])@([A-Za-z0-9_]{3,32})(?![A-Za-z0-9_])/g;

/** Distinct lowercase handles in first-seen order. */
export function mentionedHandles(text: string): string[] {
  const handles = new Set<string>();
  for (const match of text.matchAll(MENTION)) {
    const handle = match[1];
    if (handle !== undefined) handles.add(handle.toLowerCase());
  }
  return [...handles];
}

/** Append a mention to a draft with the spacing a person would type. */
export function withMention(draft: string, username: string): string {
  const mention = `@${username} `;
  if (draft === '' || /\s$/.test(draft)) return `${draft}${mention}`;
  return `${draft} ${mention}`;
}
