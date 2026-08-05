import { z } from 'zod'

import type { JobFormStepId } from '../config/job-form-steps'

const JOB_FORM_DRAFT_KEY_PREFIX = 'kyrg_job_creation_draft'
const JOB_FORM_DRAFT_VERSION = 1

const jobFormStepIdSchema = z.enum(['pipeline', 'file', 'settings', 'profile', 'review'])

const draftUserProfileSchema = z
  .object({
    product_or_solution: z.string().optional(),
    target_audience: z.string().optional(),
    core_problem: z.string().optional(),
    core_desire: z.string().optional(),
    main_promise: z.string().optional(),
    unique_mechanism: z.string().optional(),
    benefits: z.array(z.string()).optional(),
    objections: z.array(z.string()).optional(),
    proof_assets: z.array(z.string()).optional(),
    offer_details: z.string().optional(),
    call_to_action: z.string().optional(),
    tone: z.string().optional(),
    target_language: z.string().optional(),
    platform: z.string().optional(),
    desired_duration: z.number().optional(),
    restrictions: z.array(z.string()).optional(),
  })
  .strict()

const jobFormDraftValuesSchema = z
  .object({
    pipeline_type: z.enum(['copy_analysis', 'copy_adaptation']),
    source_type: z.enum(['video', 'audio']).optional(),
    language: z.string().optional(),
    need_correction: z.boolean().optional(),
    user_profile: draftUserProfileSchema.optional(),
  })
  .strict()

const jobFormDraftSchema = z
  .object({
    version: z.literal(JOB_FORM_DRAFT_VERSION),
    savedAt: z.string().datetime(),
    currentStepId: jobFormStepIdSchema,
    values: jobFormDraftValuesSchema,
  })
  .strict()

export type JobFormDraftValues = z.infer<typeof jobFormDraftValuesSchema>

export interface JobFormDraft {
  readonly currentStepId: JobFormStepId
  readonly savedAt: string
  readonly values: JobFormDraftValues
}

/**
 * Reads and validates the manually saved job form draft.
 *
 * Invalid, outdated, or unavailable browser storage is treated as no draft so
 * stale client data can never prevent the creation page from rendering.
 */
export function loadJobFormDraft(ownerId: number): JobFormDraft | null {
  const storage = getBrowserStorage()

  if (storage === null) {
    return null
  }

  try {
    const storageKey = createDraftStorageKey(ownerId)
    const serializedDraft = storage.getItem(storageKey)

    if (serializedDraft === null) {
      return null
    }

    const parsedDraft = jobFormDraftSchema.safeParse(JSON.parse(serializedDraft))

    if (!parsedDraft.success) {
      storage.removeItem(storageKey)
      return null
    }

    return parsedDraft.data
  } catch {
    return null
  }
}

/**
 * Persists the serializable fields and current wizard step on explicit user
 * action. Media files are intentionally absent because browsers cannot safely
 * restore a File reference from localStorage.
 */
export function saveJobFormDraft(
  ownerId: number,
  values: JobFormDraftValues,
  currentStepId: JobFormStepId,
): boolean {
  const storage = getBrowserStorage()

  if (storage === null) {
    return false
  }

  try {
    const draft = jobFormDraftSchema.safeParse({
      version: JOB_FORM_DRAFT_VERSION,
      savedAt: new Date().toISOString(),
      currentStepId,
      values,
    })

    if (!draft.success) {
      return false
    }

    storage.setItem(createDraftStorageKey(ownerId), JSON.stringify(draft.data))
    return true
  } catch {
    return false
  }
}

/** Remove the saved draft without affecting any submitted project. */
export function clearJobFormDraft(ownerId: number): void {
  const storage = getBrowserStorage()

  if (storage === null) {
    return
  }

  try {
    storage.removeItem(createDraftStorageKey(ownerId))
  } catch {
    // A denied storage operation must not prevent the visible form from reset.
  }
}

function createDraftStorageKey(ownerId: number): string {
  if (!Number.isInteger(ownerId) || ownerId <= 0) {
    throw new Error('Draft owner id must be a positive integer.')
  }

  return `${JOB_FORM_DRAFT_KEY_PREFIX}:${ownerId}`
}

function getBrowserStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return window.localStorage
  } catch {
    return null
  }
}
