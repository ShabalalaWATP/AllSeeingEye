import { useEffect, useMemo, useReducer, useState } from 'react';
import { useAuthStore } from '@/stores/auth';
import { subscribeWorkspaceAccess } from '@/lib/workspaceAccess';
import { drawingCollectionLayers } from '@/lib/map/drawingCollectionLayers';
import {
  emptyDrawingCollection,
  importDrawingGeoJson,
  newDrawingObject,
  validateDrawingCollection,
  validateDrawingObject,
  type DrawingCollection,
  type DrawingObject,
} from '@/lib/map/drawingCollection';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { MapDrawing } from './useMapDrawing';
import { useDrawingWorkspaceStorage } from './useDrawingWorkspaceStorage';
import { drawingAuthority } from '@/lib/map/drawingAuthority';

const initial = {
  current: emptyDrawingCollection,
  past: [] as DrawingCollection[],
  future: [] as DrawingCollection[],
};
type Action =
  | { type: 'change'; value: DrawingCollection }
  | { type: 'load'; value: DrawingCollection }
  | { type: 'select'; id: string | null }
  | { type: 'undo' | 'redo' | 'reset' };
export function drawingWorkspaceReducer(state: typeof initial, action: Action): typeof initial {
  if (action.type === 'reset') return initial;
  if (action.type === 'load') return { current: action.value, past: [], future: [] };
  if (action.type === 'select')
    return { ...state, current: { ...state.current, selectedId: action.id } };
  if (action.type === 'change')
    return {
      current: validateDrawingCollection(action.value),
      past: [...state.past, state.current].slice(-50),
      future: [],
    };
  if (action.type === 'undo') {
    const current = state.past.at(-1);
    return current
      ? {
          current,
          past: state.past.slice(0, -1),
          future: [state.current, ...state.future].slice(0, 50),
        }
      : state;
  }
  const current = state.future[0];
  return current
    ? { current, past: [...state.past, state.current].slice(-50), future: state.future.slice(1) }
    : state;
}

/** A scoped collection is independent of the current sketch and map projection. */
export function useDrawingWorkspace(drawing: MapDrawing, flat: boolean) {
  const [state, dispatch] = useReducer(drawingWorkspaceReducer, initial);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const collection = state.current;
  const selected = collection.objects.find((item) => item.id === collection.selectedId) ?? null;
  const editing = collection.objects.find((item) => item.id === editingId);
  const pendingEdits =
    drawing.anchors.length > 0 &&
    (drawing.picking ||
      drawing.shape !== editing?.shape ||
      JSON.stringify(drawing.anchors) !== JSON.stringify(editing.anchors));
  const attempt = (work: () => void) => {
    try {
      work();
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to update drawings.');
    }
  };
  const replace = (value: DrawingCollection) =>
    dispatch({ type: 'change', value: validateDrawingCollection(value) });
  const storage = useDrawingWorkspaceStorage(
    collection,
    (value) => {
      dispatch({ type: 'load', value: validateDrawingCollection(value) });
      drawing.reset();
      setEditingId(null);
    },
    pendingEdits,
  );
  useEffect(() => {
    const clear = () => {
      dispatch({ type: 'reset' });
      setError(null);
      setEditingId(null);
    };
    const offAccess = subscribeWorkspaceAccess(clear);
    const offUser = useAuthStore.subscribe((next, previous) => {
      if (drawingAuthority(next) !== drawingAuthority(previous)) clear();
    });
    return () => {
      offAccess();
      offUser();
    };
  }, []);
  const append = (object: DrawingObject) =>
    replace({ ...collection, objects: [...collection.objects, object], selectedId: object.id });
  const updateObject = (id: string, patch: Partial<Omit<DrawingObject, 'id'>>) =>
    attempt(() => {
      const item = collection.objects.find((object) => object.id === id);
      if (!item) throw new Error('Drawing no longer exists.');
      if (item.locked && Object.keys(patch).some((key) => key !== 'locked' && key !== 'visible'))
        throw new Error('Unlock the drawing before editing.');
      replace({
        ...collection,
        objects: collection.objects.map((object) =>
          object.id === id ? validateDrawingObject({ ...object, ...patch }) : object,
        ),
      });
      if (id === collection.selectedId && patch.anchors && item.shape !== 'point') {
        drawing.load(
          patch.shape === 'point' ? item.shape : (patch.shape ?? item.shape),
          patch.anchors,
        );
        setEditingId(id);
      }
      if (id === editingId && patch.visible === false) {
        drawing.clear();
        setEditingId(null);
      }
    });
  return {
    ...collection,
    canAddSketch:
      !drawing.picking && drawing.anchors.length >= (drawing.shape === 'polygon' ? 3 : 2),
    canApplySketch:
      !drawing.picking && drawing.anchors.length >= (drawing.shape === 'polygon' ? 3 : 2),
    selected,
    error,
    storage,
    layers: useMemo(
      () => drawingCollectionLayers(collection.objects, flat),
      [collection.objects, flat],
    ),
    select: (id: string | null) => {
      const item = collection.objects.find((object) => object.id === id);
      dispatch({ type: 'select', id: item?.id ?? null });
      if (item && item.shape !== 'point' && item.visible) {
        drawing.load(item.shape, item.anchors);
        setEditingId(item.id);
      } else {
        drawing.clear();
        setEditingId(null);
      }
    },
    addSketch: () =>
      attempt(() => {
        append(newDrawingObject(drawing.shape, drawing.anchors, collection.objects.length));
        drawing.clear();
        setEditingId(null);
      }),
    applySketch: () => {
      if (selected && selected.shape !== 'point' && !drawing.picking)
        updateObject(selected.id, { shape: drawing.shape, anchors: drawing.anchors });
    },
    addPoint: (point: Position) =>
      attempt(() => append(newDrawingObject('point', [point], collection.objects.length))),
    updateObject,
    duplicate: (id: string) =>
      attempt(() => {
        const item = collection.objects.find((object) => object.id === id);
        if (item)
          append({
            ...item,
            id: crypto.randomUUID(),
            name: `${item.name.slice(0, 110)} copy`,
            locked: false,
          });
      }),
    remove: (id: string) =>
      attempt(() => {
        const item = collection.objects.find((object) => object.id === id);
        if (item?.locked) throw new Error('Unlock the drawing before removing it.');
        replace({
          ...collection,
          objects: collection.objects.filter((object) => object.id !== id),
          selectedId: collection.selectedId === id ? null : collection.selectedId,
        });
        drawing.clear();
        setEditingId(null);
      }),
    clearCollection: () =>
      attempt(() => {
        if (collection.objects.some((item) => item.locked))
          throw new Error('Unlock drawings before clearing the collection.');
        replace(emptyDrawingCollection);
        drawing.clear();
        setEditingId(null);
      }),
    importGeoJson: (text: string) =>
      attempt(() => {
        const imported = importDrawingGeoJson(text);
        replace({ ...collection, objects: [...collection.objects, ...imported.objects] });
      }),
    undo: () => {
      dispatch({ type: 'undo' });
      drawing.clear();
      setEditingId(null);
    },
    redo: () => {
      dispatch({ type: 'redo' });
      drawing.clear();
      setEditingId(null);
    },
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  };
}
export type DrawingWorkspace = ReturnType<typeof useDrawingWorkspace>;
