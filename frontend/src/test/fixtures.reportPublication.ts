/**
 * A realistic frozen report publication.
 *
 * `fixtures.reportPublication.json` was produced by the backend document projector
 * (`ase.application.reports.document.build_document`) from the shared export test
 * fixture, so the reader is exercised against the blocks the API actually emits.
 * A small figure and an annex heading are appended here because the source fixture
 * does not produce either, and both block kinds need to be covered.
 */
import { reportPublicationSchema, type ReportPublication } from '@/lib/api/reports';

import raw from './fixtures.reportPublication.json';

const block = (
  kind: ReportPublication['blocks'][number]['kind'],
  text: string,
): ReportPublication['blocks'][number] => ({
  kind,
  text,
  inlines: [],
  items: [],
  ordered: false,
  table: null,
  figure: null,
});

// A 2x1 PNG: the smallest valid image that proves the figure path renders.
const PIXEL =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAFUlEQVR4nGP8//8/AzJgYkAD5AsAAJ1EAxWG6+' +
  'wAAAAASUVORK5CYII=';

const parsed = reportPublicationSchema.parse(raw);

export const reportPublication: ReportPublication = {
  ...parsed,
  blocks: [
    ...parsed.blocks,
    block('annex', 'Annex A: collection coverage'),
    {
      ...block('figure', 'Reported locations'),
      figure: {
        title: 'Figure 1. Reported locations',
        caption: 'Positions as reported by the retained sources.',
        alt_text: 'A placeholder plot of two reported locations.',
        content_base64: PIXEL,
        media_type: 'image/png',
        width_px: 2,
        height_px: 1,
        citation_numbers: [1],
      },
    },
    block('text', 'Coverage figures are recorded per collection pass for this frozen version.'),
  ],
};
