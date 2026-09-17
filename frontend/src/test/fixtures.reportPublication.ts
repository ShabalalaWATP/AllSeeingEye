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
  diagram: null,
});

// A 2x1 PNG: the smallest valid image that proves the figure path renders.
const PIXEL =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAFUlEQVR4nGP8//8/AzJgYkAD5AsAAJ1EAxWG6+' +
  'wAAAAASUVORK5CYII=';

// Drawn by the backend diagram renderer from the shared analysis fixture, so the reader
// is exercised against the markup the application actually produces.
const DIAGRAM =
  'PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCA4ODAgMTg2JyB3aWR0' +
  'aD0nMTAwJScgcm9sZT0naW1nJyBhcmlhLWxhYmVsPSdUaW1lbGluZSBvZiB0aHJlZSByZXBvcnRlZCBldmVudHM6' +
  'IGFuIGVudHJ5IGludG8gdGhlIGNpdHksIG92ZXJuaWdodCBhcnRpbGxlcnksIGFuZCB0YWxrcyByZXN1bWluZy4n' +
  'IGZvbnQtZmFtaWx5PSdzeXN0ZW0tdWksIHNhbnMtc2VyaWYnPjx0aXRsZT5SZXBvcnRlZCBzZXF1ZW5jZSBhcm91' +
  'bmQgRWwgRmFzaGVyPC90aXRsZT48ZGVzYz5UaW1lbGluZSBvZiB0aHJlZSByZXBvcnRlZCBldmVudHM6IGFuIGVu' +
  'dHJ5IGludG8gdGhlIGNpdHksIG92ZXJuaWdodCBhcnRpbGxlcnksIGFuZCB0YWxrcyByZXN1bWluZy48L2Rlc2M+' +
  'PHJlY3QgeD0nMCcgeT0nMCcgd2lkdGg9Jzg4MCcgaGVpZ2h0PScxODYnIGZpbGw9J25vbmUnLz48bGluZSB4MT0n' +
  'MTkwJyB5MT0nMjQnIHgyPScxOTAnIHkyPScxNjInIHN0cm9rZT0nI0I4QzNDQycgc3Ryb2tlLXdpZHRoPScyJy8+' +
  'PHRleHQgeD0nMjQnIHk9JzUxJyBmb250LXNpemU9JzEyJyBmaWxsPScjNTM2MTZEJyBmb250LXdlaWdodD0nNjAw' +
  'Jz4zIFNlcHRlbWJlcjwvdGV4dD48Y2lyY2xlIGN4PScxOTAnIGN5PSc0Nycgcj0nNScgZmlsbD0nIzE2OEE5Qicv' +
  'Pjx0ZXh0IHg9JzIwOCcgeT0nNTEnIGZvbnQtc2l6ZT0nMTMnIGZpbGw9JyMxMDE4MjAnPkZvcmNlcyBlbnRlcmVk' +
  'IHRoZSBjaXR5PC90ZXh0Pjx0ZXh0IHg9JzI0JyB5PSc5NycgZm9udC1zaXplPScxMicgZmlsbD0nIzUzNjE2RCcg' +
  'Zm9udC13ZWlnaHQ9JzYwMCc+NCBTZXB0ZW1iZXI8L3RleHQ+PGNpcmNsZSBjeD0nMTkwJyBjeT0nOTMnIHI9JzUn' +
  'IGZpbGw9JyMxNjhBOUInLz48dGV4dCB4PScyMDgnIHk9Jzk3JyBmb250LXNpemU9JzEzJyBmaWxsPScjMTAxODIw' +
  'Jz5BcnRpbGxlcnkgZmlyZSBvdmVybmlnaHQ8L3RleHQ+PHRleHQgeD0nMjQnIHk9JzE0MycgZm9udC1zaXplPScx' +
  'MicgZmlsbD0nIzUzNjE2RCcgZm9udC13ZWlnaHQ9JzYwMCc+NSBTZXB0ZW1iZXI8L3RleHQ+PGNpcmNsZSBjeD0n' +
  'MTkwJyBjeT0nMTM5JyByPSc1JyBmaWxsPScjMTY4QTlCJy8+PHRleHQgeD0nMjA4JyB5PScxNDMnIGZvbnQtc2l6' +
  'ZT0nMTMnIGZpbGw9JyMxMDE4MjAnPlRhbGtzIHJlc3VtZWQ8L3RleHQ+PC9zdmc+';

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
    {
      ...block(
        'diagram',
        'Timeline of three reported events: an entry into the city, ' +
          'overnight artillery, and talks resuming.',
      ),
      diagram: {
        title: 'Reported sequence around El Fasher',
        caption: 'Dates are source-reported and have not been independently verified.',
        alt_text:
          'Timeline of three reported events: an entry into the city, overnight artillery, ' +
          'and talks resuming.',
        content_base64: DIAGRAM,
        media_type: 'image/svg+xml',
        citation_numbers: [1],
      },
    },
    block('text', 'Coverage figures are recorded per collection pass for this frozen version.'),
  ],
};
