import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { DrawingCollectionControls } from './DrawingCollectionControls';
import { useDrawingWorkspace } from './useDrawingWorkspace';
import { useMapDrawing } from './useMapDrawing';
import { researchAreaGeometry } from '@/lib/map/researchAreaGeometry';

const engine = { onClick: () => () => undefined };
it('reports an unsupported research boundary and still allows editing the collection', () => {
  function Harness() {
    const drawing = useMapDrawing(engine, true);
    const workspace = useDrawingWorkspace(drawing, true);
    return (
      <>
        <button
          onClick={() =>
            drawing.load('circle', [
              [179.9, 0],
              [-179.9, 0],
            ])
          }
        >
          Prepare circle
        </button>
        <DrawingCollectionControls
          workspace={workspace}
          onResearch={(shape, anchors) => {
            researchAreaGeometry(shape, anchors);
          }}
        />
      </>
    );
  }
  render(<Harness />);
  fireEvent.click(screen.getByText('Prepare circle'));
  fireEvent.click(screen.getByText('Add sketch to collection'));
  fireEvent.click(screen.getByText('Research selected area'));
  expect(screen.getByRole('alert')).toHaveTextContent('180°');
  expect(screen.getByRole('button', { name: 'Duplicate' })).toBeEnabled();
});
it('does not discard the save click when a name field commits on blur', async () => {
  const save = vi.fn();
  function Harness() {
    const workspace = useDrawingWorkspace(useMapDrawing(engine, true), true);
    return (
      <>
        <button onClick={() => workspace.addPoint([0, 0])}>Prepare point</button>
        <DrawingCollectionControls workspace={workspace} />
        <button
          onClick={() => {
            save(workspace.selected?.name);
          }}
        >
          Save now
        </button>
      </>
    );
  }
  render(<Harness />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Prepare point'));
  await user.clear(screen.getByLabelText('Drawing name'));
  await user.type(screen.getByLabelText('Drawing name'), 'New name');
  await user.click(screen.getByText('Save now'));
  expect(save).toHaveBeenCalledWith('New name');
});
