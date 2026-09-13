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

import controlPreview from './ukraineControlPreview.json';

const control: UkraineControl = ukraineControlSchema.parse(controlPreview);
const board: UkraineBoard = { ...ukraineBoard, control: control.summary };

const loadBoard = () => Promise.resolve(board);
const loadControl = () => Promise.resolve(control);

export default function UkrainePreviewPage() {
  return (
    <div className="flex h-screen bg-ground text-text">
      <LeftRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="min-h-0 flex-1">
          <UkrainePage loadBoard={loadBoard} loadControl={loadControl} />
        </main>
      </div>
    </div>
  );
}
