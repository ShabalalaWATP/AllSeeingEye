import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import { expect, it, vi } from 'vitest';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { useGlobePanelRoute } from './useGlobePanelRoute';

const { labels, icons } = vi.hoisted(() => ({
  labels: new Map<string, number>(),
  icons: new Map<string, number>(),
}));
vi.mock('./MapControlLabel', async (load) => {
  const actual = await load<typeof import('./MapControlLabel')>();
  const React = await import('react');
  return {
    ...actual,
    MapControlLabel(props: React.ComponentProps<typeof actual.MapControlLabel>) {
      labels.set(props.label, (labels.get(props.label) ?? 0) + 1);
      return React.createElement(actual.MapControlLabel, props);
    },
  };
});
vi.mock('./MapControlIcon', async (load) => {
  const actual = await load<typeof import('./MapControlIcon')>();
  const React = await import('react');
  type Props = React.ComponentProps<typeof actual.MapControlIcon>;
  const component = actual.MapControlIcon as
    React.FunctionComponent<Props> | React.MemoExoticComponent<React.FunctionComponent<Props>>;
  const memoised = '$$typeof' in component && component.$$typeof === Symbol.for('react.memo');
  const inner = memoised ? component.type : component;
  function Counted(props: Props) {
    icons.set(props.name, (icons.get(props.name) ?? 0) + 1);
    return React.createElement(inner, props);
  }
  return { ...actual, MapControlIcon: memoised ? React.memo(Counted) : Counted };
});

function Fixture({
  version,
  onOpen,
  caption = 'Style',
  on = false,
}: {
  version: number;
  onOpen: () => void;
  caption?: string;
  on?: boolean;
}) {
  const route = useGlobePanelRoute();
  const location = useLocation();
  return (
    <>
      <output aria-label="Address">{location.search}</output>
      <GlobeControls layers={null} {...route}>
        <ControlPanel label="Map style" icon="layers" caption={caption} on={on} onOpen={onOpen}>
          <p>Current content {version}</p>
        </ControlPanel>
      </GlobeControls>
    </>
  );
}

it('does not rebuild an unchanged tool button or icons when only its panel content changes', async () => {
  const onOpen = vi.fn();
  const user = userEvent.setup();
  const fixture = (version: number) => (
    <MemoryRouter initialEntries={['/?country=GB']}>
      <Fixture version={version} onOpen={onOpen} />
    </MemoryRouter>
  );
  const view = render(fixture(1));
  expect(labels.get('Map style')).toBeGreaterThan(0);
  expect(icons.get('layers')).toBeGreaterThan(0);
  labels.clear();
  icons.clear();
  view.rerender(fixture(2));
  expect(labels.get('Map style')).toBeUndefined();
  expect(icons.size).toBe(0);
  await user.click(screen.getByRole('button', { name: 'Map style' }));
  expect(screen.getByText('Current content 2')).toBeVisible();
  expect(onOpen).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Address')).toHaveTextContent('country=GB&panel=style');
  await user.keyboard('{Escape}');
  expect(screen.getByRole('button', { name: 'Map style' })).toHaveFocus();
  expect(screen.getByLabelText('Address')).toHaveTextContent(/^\?country=GB$/);
});

it('updates visible tool metadata and invokes the latest opening callback', async () => {
  const oldOpen = vi.fn();
  const newOpen = vi.fn();
  const user = userEvent.setup();
  const view = render(
    <MemoryRouter>
      <Fixture version={1} onOpen={oldOpen} />
    </MemoryRouter>,
  );
  view.rerender(
    <MemoryRouter>
      <Fixture version={2} onOpen={newOpen} caption="Updated style" on />
    </MemoryRouter>,
  );
  const button = screen.getByRole('button', { name: 'Map style' });
  expect(button).toHaveTextContent('Updated style');
  expect(button).toHaveAttribute('data-on', 'true');
  await user.click(button);
  expect(newOpen).toHaveBeenCalledOnce();
  expect(oldOpen).not.toHaveBeenCalled();
  expect(screen.getByText('Current content 2')).toBeVisible();
  await user.click(button);
  expect(newOpen).toHaveBeenCalledOnce();
  expect(button).toHaveAttribute('aria-expanded', 'false');
});

it('keeps current route parameters and replayed history after the navigation callback changes', async () => {
  function Routed() {
    const navigate = useNavigate();
    return (
      <>
        <button onClick={() => void navigate('/?country=FR&panel=style')}>Change nation</button>
        <button onClick={() => void navigate(-1)}>Back</button>
        <Fixture version={1} onOpen={() => undefined} />
      </>
    );
  }
  render(
    <MemoryRouter initialEntries={['/?country=GB']}>
      <Routed />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Change nation' }));
  expect(screen.getByText('Current content 1')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Close tool' }));
  expect(screen.getByLabelText('Address')).toHaveTextContent(/^\?country=FR$/);
  await user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByText('Current content 1')).toBeVisible();
  expect(screen.getByLabelText('Address')).toHaveTextContent('country=FR&panel=style');
});
