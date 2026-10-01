import { describe, expect, it } from 'vitest';

import { MAX_MENTIONS, mentionedHandles, withMention } from './mentions';

describe('board mention parsing', () => {
  it('reads distinct handles like the server and ignores addresses and short tokens', () => {
    expect(mentionedHandles('@Analyst, ask @desk_lead. @analyst (@DESK_LEAD) @x12 @ab')).toEqual([
      'analyst',
      'desk_lead',
      'x12',
    ]);
    expect(mentionedHandles('lead@desk_lead.example word@analyst @@analyst')).toEqual([]);
    expect(mentionedHandles(`@${'a'.repeat(33)}`)).toEqual([]);
  });

  it('counts repeats once towards the limit', () => {
    const many = Array.from({ length: MAX_MENTIONS + 1 }, (_, n) => `@user_${String(n)}`);
    expect(mentionedHandles(`${many.join(' ')} ${many.join(' ')}`)).toHaveLength(11);
  });

  it('appends a mention with natural spacing', () => {
    expect(withMention('', 'analyst')).toBe('@analyst ');
    expect(withMention('Hello', 'analyst')).toBe('Hello @analyst ');
    expect(withMention('Hello ', 'analyst')).toBe('Hello @analyst ');
  });
});
