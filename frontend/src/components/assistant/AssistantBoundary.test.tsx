import { useEffect, useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import { AssistantBoundary } from './AssistantBoundary';
import { EyeAnswer } from './EyeAnswer';
import { eyeAnswer } from './assistantFixture';

it('contains a chat render failure, preserves the map and restarts with fresh conversation state', async () => {
  const mapMounted = vi.fn(),
    mapUnmounted = vi.fn(),
    chatUnmounted = vi.fn();
  function MapWorkspace() {
    const [zoom, setZoom] = useState(1);
    useEffect(() => {
      mapMounted();
      return () => {
        mapUnmounted();
      };
    }, []);
    return (
      <button type="button" onClick={() => setZoom(zoom + 1)}>
        Map zoom {zoom}
      </button>
    );
  }
  function Conversation() {
    const [question, setQuestion] = useState('');
    const [broken, setBroken] = useState(false);
    useEffect(
      () => () => {
        chatUnmounted();
      },
      [],
    );
    if (broken) throw new Error('Synthetic assistant render failure');
    return (
      <>
        <input
          aria-label="Conversation draft"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="button" onClick={() => setBroken(true)}>
          Trigger render failure
        </button>
      </>
    );
  }
  render(
    <>
      <MapWorkspace />
      <AssistantBoundary>
        <Conversation />
      </AssistantBoundary>
    </>,
    { onCaughtError: vi.fn() },
  );
  const user = userEvent.setup();
  const map = screen.getByRole('button', { name: 'Map zoom 1' });
  await user.click(map);
  await user.type(screen.getByLabelText('Conversation draft'), 'Discarded private draft');
  await user.click(screen.getByRole('button', { name: 'Trigger render failure' }));
  expect(screen.getByRole('button', { name: 'Map zoom 2' })).toBe(map);
  expect(mapMounted).toHaveBeenCalledTimes(1);
  expect(mapUnmounted).not.toHaveBeenCalled();
  expect(chatUnmounted).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole('button', { name: /Restart Eye assistant/ }));
  expect(screen.getByLabelText('Conversation draft')).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Map zoom 2' })).toBe(map);
  expect(document.querySelector('.eye-restart')).toBeNull();
});

it('shows an honest unknown count for an old answer retained across a hot reload', () => {
  const oldAnswer = structuredClone(eyeAnswer);
  Reflect.deleteProperty(oldAnswer.coverage, 'matched_count');
  render(
    <MemoryRouter>
      <EyeAnswer answer={oldAnswer} />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByText('Sources and coverage'));
  expect(screen.getByText(/Matched count unavailable/)).toBeVisible();
  expect(screen.getByText('Two recent vessel observations are available.')).toBeVisible();
});
