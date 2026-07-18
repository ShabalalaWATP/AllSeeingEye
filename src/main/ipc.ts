import { ipcMain, type IpcMainInvokeEvent } from 'electron'
import { z } from 'zod'
import {
  ANALYSIS_MODES,
  MAX_FOCUS_QUESTION_LENGTH,
  MAX_TEXT_LENGTH,
  REVIEW_DEPTHS,
  WINDOW_MODE_NAMES
} from '../shared/types'
import { PrefsUpdateSchema } from './core/prefs-schema'
import { VoiceAnalysisRequestSchema } from './core/voice-schema'
import { FullReviewRequestSchema } from './core/full-review-schema'
import { listCaptureSources } from './capture'
import type { AnalysisController } from './analysis'
import type { DragController } from './drag'
import type { PrefsStore } from './prefs'
import type { WindowManager } from './window'

const TextRequestSchema = z
  .object({
    text: z.string().min(1).max(MAX_TEXT_LENGTH),
    mode: z.enum(ANALYSIS_MODES),
    focusQuestion: z.string().max(MAX_FOCUS_QUESTION_LENGTH).optional(),
    depth: z.enum(REVIEW_DEPTHS).optional()
  })
  .strict()

const ScreenRequestSchema = z
  .object({
    focusQuestion: z.string().max(MAX_FOCUS_QUESTION_LENGTH).optional(),
    depth: z.enum(REVIEW_DEPTHS).optional(),
    target: z.discriminatedUnion('type', [
      z.object({ type: z.literal('display-under-pointer') }).strict(),
      z.object({
        type: z.literal('selected'),
        batchId: z.string().uuid(),
        token: z.string().uuid()
      }).strict()
    ]).optional()
  })
  .strict()

const CaptureKindSchema = z.enum(['display', 'window'])
const VoiceSessionSchema = z.string().uuid()

const WindowModeSchema = z.enum(WINDOW_MODE_NAMES)

const FitHeightSchema = z.number().int().min(100).max(1200)

/** Every argument crossing the bridge is validated here before use. */
export function registerIpc(
  controller: AnalysisController,
  prefs: PrefsStore,
  drag: DragController,
  wm: WindowManager
): void {
  const trusted = (event: IpcMainInvokeEvent): boolean =>
    event.sender === wm.win.webContents && event.senderFrame === wm.win.webContents.mainFrame

  ipcMain.handle('analysis:screen', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = ScreenRequestSchema.safeParse(raw ?? {})
    if (!parsed.success) return
    return controller.runScreen(
      parsed.data.focusQuestion,
      parsed.data.depth,
      parsed.data.target
    )
  })

  ipcMain.handle('capture:list-sources', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = CaptureKindSchema.safeParse(raw)
    if (!parsed.success) return
    return listCaptureSources(wm.win, parsed.data)
  })

  ipcMain.handle('drag:begin', (event) => trusted(event) ? drag.begin() : undefined)
  ipcMain.handle('drag:end', (event) => trusted(event) ? drag.end() : undefined)

  ipcMain.handle('analysis:text', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = TextRequestSchema.safeParse(raw)
    if (!parsed.success) return
    return controller.runText(
      parsed.data.text,
      parsed.data.mode,
      parsed.data.focusQuestion,
      parsed.data.depth
    )
  })

  ipcMain.handle('analysis:voice', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = VoiceAnalysisRequestSchema.safeParse(raw)
    if (!parsed.success) return
    return controller.runVoice(
      parsed.data.sessionId,
      new Uint8Array(parsed.data.bytes),
      parsed.data.mimeType,
      parsed.data.mode,
      parsed.data.focusQuestion,
      parsed.data.depth
    )
  })

  ipcMain.handle('voice:begin-recording', (event) =>
    trusted(event) ? controller.beginVoiceRecording() : undefined
  )

  ipcMain.handle('voice:cancel-recording', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = VoiceSessionSchema.safeParse(raw)
    if (parsed.success) controller.cancelVoiceRecording(parsed.data)
  })

  ipcMain.handle('analysis:full-review', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = FullReviewRequestSchema.safeParse(raw)
    if (!parsed.success) return false
    return controller.runFullReview(parsed.data.runId)
  })

  ipcMain.handle('window:set-mode', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = WindowModeSchema.safeParse(raw)
    if (parsed.success) controller.setWindowMode(parsed.data)
  })

  ipcMain.handle('window:set-eye-tray-open', (event, raw: unknown) => {
    if (trusted(event) && typeof raw === 'boolean') wm.setEyeTrayOpen(raw)
  })

  ipcMain.handle('window:fit-height', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = FitHeightSchema.safeParse(raw)
    if (parsed.success) controller.fitHeight(parsed.data)
  })

  ipcMain.handle('prefs:get', (event) => trusted(event) ? prefs.get() : undefined)

  ipcMain.handle('prefs:update', (event, raw: unknown) => {
    if (!trusted(event)) return
    const parsed = PrefsUpdateSchema.safeParse(raw)
    if (parsed.success) {
      prefs.set(parsed.data)
      controller.push()
    }
    return prefs.get()
  })

  ipcMain.handle('app:toggle-pause', (event) => trusted(event) ? controller.togglePause() : undefined)
  ipcMain.handle('app:dismiss', (event) => trusted(event) ? controller.dismiss() : undefined)
  ipcMain.handle('app:collapse', (event) => trusted(event) ? controller.collapse() : undefined)
  ipcMain.handle('app:quit', (event) => trusted(event) ? controller.quit() : undefined)
  ipcMain.handle('state:request', (event) => trusted(event) ? controller.push() : undefined)
}
