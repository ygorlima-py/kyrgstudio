import {
  adaptationResultSchema,
  type AdaptationMode,
  type AdaptationResultData,
  type AdaptationValidationData,
  type CorrectionAction,
  type PauseIntent,
  type ValidationCategory,
} from '../schemas/adaptation-result-schema'
import {
  normalizeAnalysisResult,
  type NormalizedAnalysisResult,
} from '@/features/copy-analysis/utils/normalize-analysis-result'
import type { CopySectionType } from '@/features/copy-analysis/schemas/analysis-result-schema'

export interface NormalizedAdaptedScriptSection {
  readonly order: number
  readonly type: CopySectionType
  readonly text: string
  readonly purpose: string
  readonly adaptationMode: AdaptationMode
  readonly sourceReferenceSectionType: string | null
  readonly proofUsed: string | null
  readonly missingProof: boolean
  readonly transitionHint: string | null
  readonly pauseIntent: PauseIntent
  readonly wordCount: number
  readonly estimatedDurationSeconds: number | null
  readonly pauseAfterSeconds: number | null
  readonly startSeconds: number | null
  readonly endSeconds: number | null
}

export interface NormalizedAdaptedScript {
  readonly script: string
  readonly sections: readonly NormalizedAdaptedScriptSection[]
  readonly hooks: readonly string[]
  readonly callToAction: string | null
  readonly estimatedDurationSeconds: number | null
  readonly wordCount: number | null
  readonly voiceReadyText: string | null
  readonly adaptationNotes: string | null
}

export interface NormalizedAdaptationValidationIssue {
  readonly category: ValidationCategory
  readonly code: string
  readonly sectionOrder: number | null
  readonly sectionType: CopySectionType | null
  readonly field: string | null
  readonly message: string
  readonly correctionAction: CorrectionAction
  readonly customInstruction: string | null
}

export interface NormalizedAdaptationValidation {
  readonly passed: boolean
  readonly errors: readonly NormalizedAdaptationValidationIssue[]
  readonly warnings: readonly NormalizedAdaptationValidationIssue[]
}

export interface NormalizedAdaptationResult {
  readonly script: NormalizedAdaptedScript
  readonly validation: NormalizedAdaptationValidation | null
  readonly missingProofs: readonly string[]
  readonly referenceAnalysis: NormalizedAnalysisResult
}

/** Controlled error raised when persisted adaptation output is not public-safe. */
export class AdaptationResultValidationError extends Error {
  readonly code = 'invalid_adaptation_result'

  constructor() {
    super('The copy adaptation result has an invalid public structure.')
    this.name = 'AdaptationResultValidationError'
  }
}

/**
 * Validate unknown API data and convert it into the stable view model consumed
 * by copy-adaptation components.
 */
export function normalizeAdaptationResult(value: unknown): NormalizedAdaptationResult {
  const parsedResult = adaptationResultSchema.safeParse(value)

  if (!parsedResult.success) {
    throw new AdaptationResultValidationError()
  }

  return buildNormalizedResult(parsedResult.data)
}

function buildNormalizedResult(result: AdaptationResultData): NormalizedAdaptationResult {
  return {
    script: {
      script: result.adapted_script.script,
      sections: result.adapted_script.sections.map((section) => ({
        order: section.order,
        type: section.section_type,
        text: section.text,
        purpose: section.purpose,
        adaptationMode: section.adaptation_mode,
        sourceReferenceSectionType: section.source_reference_section_type,
        proofUsed: section.proof_used,
        missingProof: section.missing_proof,
        transitionHint: section.transition_hint,
        pauseIntent: section.pause_intent,
        wordCount: section.word_count,
        estimatedDurationSeconds: section.estimated_duration_seconds,
        pauseAfterSeconds: section.pause_after_seconds,
        startSeconds: section.start_seconds,
        endSeconds: section.end_seconds,
      })),
      hooks: [...result.adapted_script.hooks],
      callToAction: result.adapted_script.cta,
      estimatedDurationSeconds: result.adapted_script.estimated_duration_seconds,
      wordCount: result.adapted_script.word_count,
      voiceReadyText: result.adapted_script.voice_ready_text,
      adaptationNotes: result.adapted_script.adaptation_notes,
    },
    validation: normalizeValidation(result.validation),
    missingProofs: [...result.missing_proofs],
    referenceAnalysis: normalizeAnalysisResult(result.copy_analysis),
  }
}

function normalizeValidation(
  validation: AdaptationValidationData | null,
): NormalizedAdaptationValidation | null {
  if (validation === null) {
    return null
  }

  return {
    passed: validation.validation_passed,
    errors: validation.validation_errors.map(normalizeValidationIssue),
    warnings: validation.validation_warnings.map(normalizeValidationIssue),
  }
}

function normalizeValidationIssue(
  issue: AdaptationValidationData['validation_errors'][number],
): NormalizedAdaptationValidationIssue {
  return {
    category: issue.category,
    code: issue.code,
    sectionOrder: issue.section_order,
    sectionType: issue.section_type,
    field: issue.field,
    message: issue.message,
    correctionAction: issue.correction_action,
    customInstruction: issue.custom_instruction,
  }
}
