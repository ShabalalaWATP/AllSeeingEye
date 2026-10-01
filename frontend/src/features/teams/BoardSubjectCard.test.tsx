import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { TeamBoardPost } from '@/lib/api/teamBoard';
import { plainUser } from '@/test/fixtures';
import { boardPost } from '@/test/fixtures.teamBoard';

import { BoardPostCard } from './BoardPostCard';
import { BoardSubjectCard } from './BoardSubjectCard';

const reportId = '22222222-2222-4222-8222-222222222222';

function renderCard(post: TeamBoardPost) {
  return render(
    <MemoryRouter>
      <BoardPostCard
        post={post}
        userId={plainUser.id}
        canModerate={false}
        canWrite
        busy={false}
        onEdit={vi.fn()}
        onReply={vi.fn()}
        onModerate={vi.fn()}
      />
    </MemoryRouter>,
  );
}

describe('BoardSubjectCard', () => {
  it('shows an available report version as a title card linking to that exact version', () => {
    renderCard(
      boardPost({
        subject: {
          kind: 'report_version',
          id: reportId,
          version: 2,
          available: true,
          title: 'Port <b>activity</b> review',
        },
      }),
    );
    const card = screen.getByRole('group', { name: 'Linked report version' });
    const link = within(card).getByRole('link', { name: /Port <b>activity<\/b> review/ });
    expect(link).toHaveAttribute('href', `/reports/${reportId}?version=2`);
    expect(within(card).getByText('Report version 2')).toBeInTheDocument();
    // Titles stay text: markup in a title is never interpreted.
    expect(card.querySelector('b')).toBeNull();
  });

  it('shows saved areas and drawing collections by title without inventing a route', () => {
    render(
      <>
        <BoardSubjectCard
          subject={{
            kind: 'saved_area',
            id: reportId,
            version: null,
            available: true,
            title: 'Northern approaches',
          }}
        />
        <BoardSubjectCard
          subject={{
            kind: 'drawing_collection',
            id: reportId,
            version: null,
            available: true,
            title: 'Patrol sketches',
          }}
        />
      </>,
    );
    expect(screen.getByRole('group', { name: 'Linked saved area' })).toHaveTextContent(
      'Northern approaches',
    );
    expect(screen.getByRole('group', { name: 'Linked drawing collection' })).toHaveTextContent(
      'Patrol sketches',
    );
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('marks an inaccessible subject as unavailable without a title or link', () => {
    renderCard(
      boardPost({
        subject: { kind: 'report_version', id: null, version: 1, available: false, title: null },
      }),
    );
    const card = screen.getByRole('group', { name: 'Linked report version' });
    expect(card).toHaveTextContent('Linked item unavailable');
    expect(card).toHaveTextContent('You can no longer open this item');
    expect(within(card).queryByRole('link')).not.toBeInTheDocument();
  });

  it('shows no card for ordinary posts or removed posts', () => {
    renderCard(boardPost({ subject: null }));
    renderCard(
      boardPost({
        id: '66666666-6666-4666-8666-666666666662',
        deleted_at: '2026-09-15T09:00:00Z',
        removal: 'author',
        text: '[Removed by author]',
      }),
    );
    expect(screen.queryByRole('group', { name: /Linked/ })).not.toBeInTheDocument();
  });

  it('highlights the thread a link points to', () => {
    render(
      <BoardPostCard
        post={boardPost({})}
        userId={plainUser.id}
        canModerate={false}
        canWrite={false}
        busy={false}
        highlighted
        onEdit={vi.fn()}
        onReply={vi.fn()}
        onModerate={vi.fn()}
      />,
    );
    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('id', 'board-post-66666666-6666-4666-8666-666666666661');
    expect(article).toHaveAttribute('aria-current', 'true');
  });
});
