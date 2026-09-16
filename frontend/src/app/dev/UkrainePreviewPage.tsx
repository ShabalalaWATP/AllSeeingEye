/**
 * Development-only page (registered when import.meta.env.DEV) that frames the Ukraine war
 * tracker with fixture data: the board fixture plus a reduced copy of the packaged control
 * snapshot, so the map, tabs and figures can be checked without an account. Nothing here
 * reaches the API with a credential.
 */
import { LeftRail } from '@/app/shell/LeftRail';
import { TopBar } from '@/app/shell/TopBar';
import UkrainePage from '@/features/ukraine/UkrainePage';
import { ukraineControlSchema, type UkraineBoard, type UkraineControl } from '@/lib/api/ukraine';
import { ukraineBoard } from '@/test/fixtures.ukraine';
import { ukraineDigest } from '@/test/fixtures.ukraineDigest';
import { ukraineFrontlineReady, ukraineSpottedReady } from '@/test/fixtures.ukraineFigures';
import { ukraineReference } from '@/test/fixtures.ukraineReference';

import invasionDay from './invasion-day.jpg';
import orlan from './ru-orlan-10.jpg';
import supreme from './ru-supreme.jpg';
import t90m from './ru-t-90m.jpg';
import controlPreview from './ukraineControlPreview.json';

const control: UkraineControl = ukraineControlSchema.parse(controlPreview);
const board: UkraineBoard = { ...ukraineBoard, control: control.summary };

const loadBoard = () => Promise.resolve(board);
const loadControl = () => Promise.resolve(control);
const loadReference = () => Promise.resolve(ukraineReference);
const loadDigest = () => Promise.resolve(ukraineDigest);
const mapLoaders = {
  frontline: () => Promise.resolve(ukraineFrontlineReady),
  spotted: () => Promise.resolve(ukraineSpottedReady),
};
const previewImages: Record<string, string> = {
  'ru-orlan-10': orlan,
  'ru-t-90m': t90m,
  'ru-supreme': supreme,
  'invasion-day': invasionDay,
};
/** Serves the three bundled sample images in place of the authenticated image endpoint. */
const imageFetcher = (path: string): Promise<Blob> => {
  const id =
    path
      .split('/')
      .pop()
      ?.replace(/\.jpg$/, '') ?? '';
  const url = previewImages[id];
  return url ? fetch(url).then((r) => r.blob()) : Promise.reject(new Error('no preview image'));
};

export default function UkrainePreviewPage() {
  return (
    <div className="flex h-screen bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1">
          <UkrainePage
            loadBoard={loadBoard}
            loadControl={loadControl}
            loadReference={loadReference}
            loadDigest={loadDigest}
            refreshDigest={loadDigest}
            imageFetcher={imageFetcher}
            mapLoaders={mapLoaders}
          />
        </main>
      </div>
    </div>
  );
}
