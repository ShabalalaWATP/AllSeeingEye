import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { DrawingCollectionControls } from './DrawingCollectionControls';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { useMapDrawing } from './useMapDrawing';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';

const engine = { onClick: () => () => undefined };
const input = JSON.stringify({
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Imported marker' },
      geometry: { type: 'Point', coordinates: [-2, 54] },
    },
  ],
});
function Harness({ radio = () => undefined }: { radio?: (point: [number, number]) => void }) {
  const workspace = useDrawingWorkspace(useMapDrawing(engine, true), true);
  return (
    <>
      <DrawingCollectionControls workspace={workspace} onRadioSite={radio} />
      <output aria-label="Collection data">{JSON.stringify(workspace.objects)}</output>
    </>
  );
}
function addPoint() {
  fireEvent.click(screen.getByText('Add a named point'));
  fireEvent.change(screen.getByLabelText('New point longitude'), { target: { value: '-2' } });
  fireEvent.change(screen.getByLabelText('New point latitude'), { target: { value: '54' } });
  fireEvent.click(screen.getByRole('button', { name: 'Add point' }));
}
function upload(file: File) {
  fireEvent.change(screen.getByLabelText('Import drawing GeoJSON'), { target: { files: [file] } });
}
it('adds a point, edits metadata, protects locked content and hands its coordinates to radio', () => {
  const radio = vi.fn();
  render(<Harness radio={radio} />);
  fireEvent.click(screen.getByRole('button', { name: 'Add point' }));
  expect(screen.getByRole('alert')).toHaveTextContent('longitude and latitude');
  addPoint();
  fireEvent.blur(screen.getByLabelText('Drawing name'));
  fireEvent.change(screen.getByLabelText('Drawing notes'), {
    target: { value: 'Observation location' },
  });
  fireEvent.blur(screen.getByLabelText('Drawing notes'));
  fireEvent.blur(screen.getByLabelText('Drawing notes'));
  fireEvent.change(screen.getByLabelText('Drawing colour'), { target: { value: '#ff7700' } });
  fireEvent.click(screen.getByLabelText('Visible'));
  fireEvent.click(screen.getByLabelText('Locked'));
  expect(screen.getByLabelText('Drawing name')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Remove' })).toBeDisabled();
  expect(screen.getByLabelText('Collection data')).toHaveTextContent('Observation location');
  expect(screen.getByLabelText('Collection data')).toHaveTextContent('#ff7700');
  fireEvent.click(screen.getByRole('button', { name: 'Use as radio site' }));
  expect(radio).toHaveBeenCalledWith([-2, 54]);
  fireEvent.click(screen.getByLabelText('Locked'));
  fireEvent.click(screen.getByRole('button', { name: 'Duplicate' }));
  const select = screen.getByLabelText('Selected drawing');
  fireEvent.change(select, { target: { value: '' } });
  expect(screen.queryByLabelText('Drawing name')).not.toBeInTheDocument();
  const option = screen.getByRole<HTMLOptionElement>('option', { name: 'Point 1' });
  fireEvent.change(select, { target: { value: option.value } });
  fireEvent.click(screen.getByRole('button', { name: 'Remove' }));
  expect(screen.queryByRole('option', { name: 'Point 1' })).not.toBeInTheDocument();
});
it('imports a file and rejects a file over the byte limit', async () => {
  render(<Harness />);
  const file = new File([input], 'markers.geojson');
  Object.defineProperty(file, 'text', { value: () => Promise.resolve(input) });
  upload(file);
  await waitFor(() =>
    expect(screen.getByRole('option', { name: 'Imported marker' })).toBeInTheDocument(),
  );
  upload(new File([' '.repeat(128 * 1024 + 1)], 'large.geojson'));
  expect(screen.getByRole('alert')).toHaveTextContent('128 KiB');
  fireEvent.change(screen.getByLabelText('Import drawing GeoJSON'), { target: { files: [] } });
});
it('shows a file read error and discards a delayed import after access changes', async () => {
  render(<Harness />);
  const broken = new File([], 'broken.geojson');
  Object.defineProperty(broken, 'text', {
    value: () => Promise.reject(new Error('Unavailable file')),
  });
  upload(broken);
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Unable to read'));
  let resolve: (text: string) => void = () => undefined;
  const delayed = new File([], 'delayed.geojson');
  Object.defineProperty(delayed, 'text', {
    value: () =>
      new Promise<string>((done) => {
        resolve = done;
      }),
  });
  upload(delayed);
  act(() => invalidateWorkspaceAccess());
  await act(async () => {
    resolve(input);
    await Promise.resolve();
  });
  expect(screen.queryByRole('option', { name: 'Imported marker' })).not.toBeInTheDocument();
});
it('exports a downloadable GeoJSON collection and releases the object URL', async () => {
  const create = vi.fn(() => 'blob:drawing-export');
  const revoke = vi.fn();
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
  const oldCreate = Object.getOwnPropertyDescriptor(URL, 'createObjectURL');
  const oldRevoke = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL');
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: create });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revoke });
  try {
    render(<Harness />);
    addPoint();
    fireEvent.click(screen.getByRole('button', { name: 'Export GeoJSON' }));
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ type: 'application/geo+json' }));
    expect(click).toHaveBeenCalledOnce();
    await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:drawing-export'));
  } finally {
    if (oldCreate) Object.defineProperty(URL, 'createObjectURL', oldCreate);
    else Reflect.deleteProperty(URL, 'createObjectURL');
    if (oldRevoke) Object.defineProperty(URL, 'revokeObjectURL', oldRevoke);
    else Reflect.deleteProperty(URL, 'revokeObjectURL');
  }
});
