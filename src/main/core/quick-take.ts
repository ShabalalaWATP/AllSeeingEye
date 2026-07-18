import { z } from 'zod'
import { truncate } from './finding-schema'

export const QUICK_TAKE_MAX_LENGTH = 96

export const QuickTakeSchema = z.object({
  answer: z.string().min(1).max(QUICK_TAKE_MAX_LENGTH)
}).strict()

export type QuickTake = z.infer<typeof QuickTakeSchema>

export function sanitiseQuickTake(value: QuickTake): string {
  return truncate(value.answer.trim(), QUICK_TAKE_MAX_LENGTH)
}
