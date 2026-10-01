import { SelectField } from '@/components/ui/Field';
import type { TeamMember } from '@/lib/api/teams';
import { MAX_MENTIONS, mentionedHandles, withMention } from '@/lib/mentions';

/** True when the draft names more different teammates than one post may notify. */
export function tooManyMentions(draft: string): boolean {
  return mentionedHandles(draft).length > MAX_MENTIONS;
}

/**
 * Insert a teammate's handle into the draft with a native, keyboard-operable select.
 * Only this team's roster is offered (active members with a directory username, never
 * the author). The server resolves handles again when the post is saved.
 */
export function BoardMentionPicker({
  members,
  userId,
  draft,
  disabled,
  onDraftChange,
}: {
  members: readonly TeamMember[];
  userId: string;
  draft: string;
  disabled: boolean;
  onDraftChange: (draft: string) => void;
}) {
  const choices = members.filter(
    (member) => member.is_active && member.username !== null && member.user_id !== userId,
  );
  const count = mentionedHandles(draft).length;
  const over = count > MAX_MENTIONS;
  return (
    <div className="mt-3 flex flex-col gap-1">
      {choices.length > 0 ? (
        <SelectField
          label="Mention a teammate"
          hint="Mentioned teammates see the post in their notifications. Only current members with a directory username can be mentioned."
          value=""
          disabled={disabled}
          onChange={(event) => {
            if (event.target.value) onDraftChange(withMention(draft, event.target.value));
          }}
          options={[
            { value: '', label: 'Choose a teammate' },
            ...choices.map((member) => ({
              value: member.username ?? '',
              label: `${member.display_name} (@${member.username ?? ''})`,
            })),
          ]}
        />
      ) : (
        <p className="text-xs text-muted">
          Teammates can be mentioned once they choose a directory username.
        </p>
      )}
      <p
        aria-live="polite"
        className={over ? 'text-xs font-medium text-critical' : 'text-xs text-muted'}
      >
        {over
          ? `This post mentions ${String(count)} different people. A post can mention up to ${String(MAX_MENTIONS)}; remove some to post.`
          : count > 0
            ? `${String(count)} of up to ${String(MAX_MENTIONS)} mentions used.`
            : ''}
      </p>
    </div>
  );
}
