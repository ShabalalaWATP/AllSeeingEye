# Public product page specification

This folder describes the public product story at `/enterprise` (KAN-170) as it is
built in `frontend/src/features/product/`. It is the KAN-171 content and design
specification. It records what the page says and does, checks each capability claim
against the repository, and lists the copy and motion points that need a decision.

## Status

**Draft for Alex's approval. Nothing in this folder is approved yet.**

- Written on 18 October 2026 against branch `claude/KAN-170-product-gaps`, which
  holds `main` at `ea68f65c` plus the integrated KAN-173 to KAN-180 and KAN-196
  product page work. That work is not yet merged to `main`.
- The documents describe the existing code. They do not propose a new design.
  Where the build differs from the KAN-170 or KAN-171 ticket text, the difference
  is recorded rather than resolved.
- No copy, motion or code was changed while writing them. Copy issues are listed
  in [narrative.md](narrative.md#copy-issues-for-review) for Alex to decide.
- The cost estimator's figures are outside this specification. They are drafts
  governed by `content/costModel.ts` and KAN-178, and production builds do not show
  the estimator until `COST_MODEL_STATUS` is `'approved'`.
- The licence and offer wording (KAN-164, ADR 0023) is undecided. The closing
  chapter's promise of help is listed as a copy issue for that reason.

## Files

| File | What it holds |
| --- | --- |
| [narrative.md](narrative.md) | Each chapter in page order: headline, explanation and supporting points quoted from the code, then copy issues for review |
| [claims-register.md](claims-register.md) | One row per capability claim, with the evidence opened, caveats, the date verified and a status |
| [honest-limits.md](honest-limits.md) | The five limits adapted from the README and where each appears on the page |
| [storyboard.md](storyboard.md) | One frame per chapter: start, scroll transition, end state, text position by width and the still version |
| [motion-spec.md](motion-spec.md) | Easing, durations, staggers, the animatable-property rule and its exceptions, pinning and scroll distance, the scheduler, pointer follow, pause and device handling |
| [visual-direction.md](visual-direction.md) | Palette and tokens, typefaces, layer and topic colours, depth and glow, the fixed dark palette and the performance budget |

The narrative supplies the words. The claims register is the check on those words:
every factual statement in the narrative should have a row there. The storyboard
and motion specification describe how the same chapters move, and the visual
direction describes how they look. The honest limits are a subset of the narrative
that is deliberately kept static.

## Review rule

1. Alex reviews the narrative, storyboard and claims register together.
2. Every claim marked Verified or Caveat is re-verified against `main` within
   **7 days of approval**. Re-verification means opening the evidence again, not
   re-reading this register.
3. Claims are verified again on **release day**, against the commit being
   deployed. The source catalogue counts are re-counted with the method in
   [claims-register.md](claims-register.md#source-catalogue-recount).
4. Any claim marked Unverified is cut from the page, or reworded and re-verified,
   before release.
5. A claim that describes a feature not merged to `main` on release day is cut.
6. Each re-verification updates the "Verified" column with the new date and the
   commit it was checked against.

## Related records

- [Public product page acceptance](../PUBLIC_PRODUCT_PAGE_ACCEPTANCE.md): route
  gating, metadata, bundle budget and browser measurements.
- [Architecture](../01_ARCHITECTURE.md), [Security and privacy](../07_SECURITY_BY_DESIGN.md),
  [Reporting and assessment](../03_DOCTRINE_AND_REPORTING.md) and [AI](../AI.md):
  the main evidence for the claims register.
- [ADR 0023](../adr/0023-software-licence-and-offer.md): licence and offer, pending.
