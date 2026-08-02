import { z } from 'zod'

import {
  analysisResultSchema,
  copySectionTypeSchema,
} from '@/features/copy-analysis/schemas/analysis-result-schema'

const ADAPTATION_MODES = ['adapted_from_reference', 'created_from_scratch'] as const
const PAUSE_INTENTS = ['short', 'medium', 'long', 'dramatic'] as const
const VALIDATION_CATEGORIES = [
  'claim',
  'proof',
  'offer',
  'cta',
  'scarcity',
  'duration',
  'language',
  'structure',
  'copy_similarity',
  'other',
] as const
const CORRECTION_ACTIONS = [
  'remove',
  'soften',
  'rewrite',
  'shorten',
  'expand',
  'align_with_profile',
  'custom',
] as const

const requiredTextSchema = z.string().trim().min(1)

const optionalTextSchema = z
  .string()
  .trim()
  .nullable()
  .optional()
  .transform((value) => value || null)

const optionalNonNegativeNumberSchema = z
  .number()
  .finite()
  .nonnegative()
  .nullable()
  .optional()
  .transform((value) => value ?? null)

const optionalNonNegativeIntegerSchema = z
  .number()
  .int()
  .nonnegative()
  .nullable()
  .optional()
  .transform((value) => value ?? null)

const optionalPositiveIntegerSchema = z
  .number()
  .int()
  .positive()
  .nullable()
  .optional()
  .transform((value) => value ?? null)

export const adaptationModeSchema = z.enum(ADAPTATION_MODES)
export const pauseIntentSchema = z.enum(PAUSE_INTENTS)
export const validationCategorySchema = z.enum(VALIDATION_CATEGORIES)
export const correctionActionSchema = z.enum(CORRECTION_ACTIONS)

/** One ordered and timed section of the public adapted script. */
export const adaptedScriptSectionSchema = z.object({
  order: z.number().int().positive(),
  section_type: copySectionTypeSchema,
  text: requiredTextSchema,
  purpose: requiredTextSchema,
  adaptation_mode: adaptationModeSchema,
  source_reference_section_type: optionalTextSchema,
  proof_used: optionalTextSchema,
  missing_proof: z.boolean(),
  transition_hint: optionalTextSchema,
  pause_intent: pauseIntentSchema,
  word_count: z.number().int().nonnegative(),
  estimated_duration_seconds: optionalNonNegativeNumberSchema,
  pause_after_seconds: optionalNonNegativeNumberSchema,
  start_seconds: optionalNonNegativeNumberSchema,
  end_seconds: optionalNonNegativeNumberSchema,
})

/** Editable script fields allowed by the backend's public response contract. */
export const adaptedScriptSchema = z.object({
  script: requiredTextSchema,
  sections: z.array(adaptedScriptSectionSchema).default([]),
  hooks: z.array(requiredTextSchema).default([]),
  cta: optionalTextSchema,
  estimated_duration_seconds: optionalNonNegativeNumberSchema,
  word_count: optionalNonNegativeIntegerSchema,
  voice_ready_text: optionalTextSchema,
  adaptation_notes: optionalTextSchema,
})

/** A blocking error or non-blocking warning produced by script validation. */
export const adaptationValidationIssueSchema = z.object({
  category: validationCategorySchema,
  code: requiredTextSchema,
  section_order: optionalPositiveIntegerSchema,
  section_type: copySectionTypeSchema
    .nullable()
    .optional()
    .transform((value) => value ?? null),
  field: optionalTextSchema,
  message: requiredTextSchema,
  correction_action: correctionActionSchema,
  custom_instruction: optionalTextSchema,
})

export const adaptationValidationSchema = z
  .object({
    validation_passed: z.boolean(),
    validation_errors: z.array(adaptationValidationIssueSchema).default([]),
    validation_warnings: z.array(adaptationValidationIssueSchema).default([]),
  })
  .nullable()
  .optional()
  .transform((value) => value ?? null)

/**
 * Runtime boundary for the public copy-adaptation output returned by the API.
 *
 * Zod strips unknown properties from every object, keeping worker diagnostics,
 * provider metadata and fields outside the public contract away from the UI.
 */
export const adaptationResultSchema = z.object({
  adapted_script: adaptedScriptSchema,
  validation: adaptationValidationSchema,
  missing_proofs: z.array(requiredTextSchema).default([]),
  copy_analysis: analysisResultSchema,
})

export type AdaptationMode = z.output<typeof adaptationModeSchema>
export type PauseIntent = z.output<typeof pauseIntentSchema>
export type ValidationCategory = z.output<typeof validationCategorySchema>
export type CorrectionAction = z.output<typeof correctionActionSchema>
export type AdaptedScriptSectionData = z.output<typeof adaptedScriptSectionSchema>
export type AdaptedScriptData = z.output<typeof adaptedScriptSchema>
export type AdaptationValidationIssueData = z.output<typeof adaptationValidationIssueSchema>
export type AdaptationValidationData = Exclude<z.output<typeof adaptationValidationSchema>, null>
export type AdaptationResultData = z.output<typeof adaptationResultSchema>
