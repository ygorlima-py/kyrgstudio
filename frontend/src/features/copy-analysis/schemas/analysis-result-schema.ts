import { z } from 'zod'

const SECTION_TYPES = [
  'hook',
  'problem',
  'pain',
  'agitation',
  'promise',
  'mechanism',
  'proof',
  'story',
  'objection',
  'offer',
  'cta',
  'urgency',
  'scarcity',
  'transition',
  'education',
  'payoff',
] as const

const requiredTextSchema = z.string().trim().min(1)

const optionalTextSchema = z
  .string()
  .trim()
  .nullable()
  .optional()
  .transform((value) => value || null)

const optionalNumberSchema = z
  .number()
  .finite()
  .nullable()
  .optional()
  .transform((value) => value ?? null)

export const copySectionTypeSchema = z.enum(SECTION_TYPES)

export const copySectionSchema = z.object({
  section_type: copySectionTypeSchema,
  text: requiredTextSchema,
  purpose: requiredTextSchema,
  start: optionalNumberSchema,
  end: optionalNumberSchema,
})

export const sectionGapSchema = z.object({
  section_type: copySectionTypeSchema,
  gap_type: z.enum(['missing', 'incomplete', 'weak']),
  reason: requiredTextSchema,
})

export const copyStructureSchema = z.object({
  language: optionalTextSchema,
  content_type: requiredTextSchema,
  main_hook: optionalTextSchema,
  sections: z.array(copySectionSchema).default([]),
  narrative_flow: z.array(requiredTextSchema).default([]),
  section_gaps: z.array(sectionGapSchema).default([]),
  summary: requiredTextSchema,
})

export const offerElementSchema = z.object({
  name: requiredTextSchema,
  description: requiredTextSchema,
  evidence: optionalTextSchema,
})

export const offerAnalysisSchema = z.object({
  product_or_solution: optionalTextSchema,
  target_audience: optionalTextSchema,
  core_problem: optionalTextSchema,
  core_desire: optionalTextSchema,
  main_promise: optionalTextSchema,
  unique_mechanism: optionalTextSchema,
  benefits: z.array(offerElementSchema).default([]),
  objections: z.array(offerElementSchema).default([]),
  proof_elements: z.array(offerElementSchema).default([]),
  bonuses: z.array(offerElementSchema).default([]),
  urgency_or_scarcity: z.array(offerElementSchema).default([]),
  call_to_action: optionalTextSchema,
  price_or_terms: optionalTextSchema,
  summary: requiredTextSchema,
})

export const persuasionSignalSchema = z.object({
  name: requiredTextSchema,
  description: requiredTextSchema,
  evidence: optionalTextSchema,
  strength: requiredTextSchema,
})

export const persuasionWeaknessSchema = z.object({
  issue: requiredTextSchema,
  impact: requiredTextSchema,
  evidence: optionalTextSchema,
})

export const persuasionAnalysisSchema = z.object({
  dominant_emotion: optionalTextSchema,
  persuasion_pattern: optionalTextSchema,
  hook_strength: optionalTextSchema,
  promise_clarity: optionalTextSchema,
  proof_strength: optionalTextSchema,
  urgency_strength: optionalTextSchema,
  cta_strength: optionalTextSchema,
  persuasion_signals: z.array(persuasionSignalSchema).default([]),
  weaknesses: z.array(persuasionWeaknessSchema).default([]),
  summary: requiredTextSchema,
})

/**
 * Runtime boundary for the public copy analysis returned by the API.
 *
 * Zod objects strip unknown properties by default, so worker-only or future
 * internal fields cannot reach presentation components accidentally.
 */
export const analysisResultSchema = z.object({
  language: optionalTextSchema,
  copy_structure: copyStructureSchema,
  offer_analysis: offerAnalysisSchema,
  persuasion_analysis: persuasionAnalysisSchema,
})

/** Public transcription fields allowed to cross the presentation boundary. */
export const publicTranscriptionSchema = z.object({
  language: optionalTextSchema,
  text: requiredTextSchema,
})

export type CopySectionType = z.output<typeof copySectionTypeSchema>
export type CopySectionData = z.output<typeof copySectionSchema>
export type SectionGapData = z.output<typeof sectionGapSchema>
export type CopyStructureData = z.output<typeof copyStructureSchema>
export type OfferElementData = z.output<typeof offerElementSchema>
export type OfferAnalysisData = z.output<typeof offerAnalysisSchema>
export type PersuasionSignalData = z.output<typeof persuasionSignalSchema>
export type PersuasionWeaknessData = z.output<typeof persuasionWeaknessSchema>
export type PersuasionAnalysisData = z.output<typeof persuasionAnalysisSchema>
export type AnalysisResultData = z.output<typeof analysisResultSchema>
export type PublicTranscriptionData = z.output<typeof publicTranscriptionSchema>
