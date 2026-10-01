/** Reader-facing wording for what a team copy carries and what stays personal. */
import type { TeamCopyOmission, TeamCopyPreview } from '@/lib/api/reportTeamCopies';

export const COPIED_CONTENT =
  'The analysis, figures, findings, frozen evidence with its content hashes, quality and ' +
  'assessment values, exactly as saved in this version.';

export const OMISSION_TEXT: Record<TeamCopyOmission, string> = {
  research_brief: 'The link to your Research Brief is not copied.',
  claim_generation: 'The claim ledger receipt is not copied; the team copy starts without claims.',
  original_passages:
    'Retained original passages are not copied; their receipts show them as not carried over.',
  source_assessment:
    'The frozen source assessment could not be carried over and is shown as unavailable.',
  scope_references:
    'Links to your plans, parent reports, subscription baselines and uploaded inputs stay private.',
};

const NOT_COPIED: Record<keyof TeamCopyPreview['not_copied'], [string, string]> = {
  claims: ['claim ledger entry', 'claim ledger entries'],
  original_files: ['retained original file', 'retained original files'],
  original_passages: ['retained original passage', 'retained original passages'],
  reviewed_snapshots: ['reviewed source snapshot', 'reviewed source snapshots'],
  map_views: ['saved map view', 'saved map views'],
};

/** Non-zero counts of linked personal records that stay with the original. */
export function notCopiedLines(counts: TeamCopyPreview['not_copied']): string[] {
  return (Object.keys(NOT_COPIED) as (keyof typeof NOT_COPIED)[])
    .filter((key) => counts[key] > 0)
    .map((key) => {
      const [one, many] = NOT_COPIED[key];
      return counts[key] === 1
        ? `1 ${one} stays with your personal report.`
        : `${counts[key]} ${many} stay with your personal report.`;
    });
}
