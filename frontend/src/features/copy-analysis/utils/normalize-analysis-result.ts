import { analysisResultSchema, publicTranscriptionSchema } from '../schemas/analysis-result-schema'
import type { AnalysisResultData, CopySectionType } from '../schemas/analysis-result-schema'

export interface NormalizedCopySection {
  readonly type: CopySectionType
  readonly text: string
  readonly purpose: string
  readonly startSeconds: number | null
  readonly endSeconds: number | null
}

export interface NormalizedSectionGap {
  readonly sectionType: CopySectionType
  readonly gapType: 'missing' | 'incomplete' | 'weak'
  readonly reason: string
}

export interface NormalizedCopyStructure {
  readonly language: string | null
  readonly contentType: string
  readonly mainHook: string | null
  readonly sections: readonly NormalizedCopySection[]
  readonly narrativeFlow: readonly string[]
  readonly gaps: readonly NormalizedSectionGap[]
  readonly summary: string
}

export interface NormalizedOfferElement {
  readonly name: string
  readonly description: string
  readonly evidence: string | null
}

export interface NormalizedOfferAnalysis {
  readonly productOrSolution: string | null
  readonly targetAudience: string | null
  readonly coreProblem: string | null
  readonly coreDesire: string | null
  readonly mainPromise: string | null
  readonly uniqueMechanism: string | null
  readonly benefits: readonly NormalizedOfferElement[]
  readonly objections: readonly NormalizedOfferElement[]
  readonly proofElements: readonly NormalizedOfferElement[]
  readonly bonuses: readonly NormalizedOfferElement[]
  readonly urgencyOrScarcity: readonly NormalizedOfferElement[]
  readonly callToAction: string | null
  readonly priceOrTerms: string | null
  readonly summary: string
}

export interface NormalizedPersuasionSignal {
  readonly name: string
  readonly description: string
  readonly evidence: string | null
  readonly strength: string
}

export interface NormalizedPersuasionWeakness {
  readonly issue: string
  readonly impact: string
  readonly evidence: string | null
}

export interface NormalizedPersuasionStrengths {
  readonly hook: string | null
  readonly promiseClarity: string | null
  readonly proof: string | null
  readonly urgency: string | null
  readonly callToAction: string | null
}

export interface NormalizedPersuasionAnalysis {
  readonly dominantEmotion: string | null
  readonly pattern: string | null
  readonly strengths: NormalizedPersuasionStrengths
  readonly signals: readonly NormalizedPersuasionSignal[]
  readonly weaknesses: readonly NormalizedPersuasionWeakness[]
  readonly summary: string
}

export interface NormalizedAnalysisResult {
  readonly language: string | null
  readonly structure: NormalizedCopyStructure
  readonly offer: NormalizedOfferAnalysis
  readonly persuasion: NormalizedPersuasionAnalysis
}

export interface NormalizedTranscription {
  readonly language: string | null
  readonly text: string
}

/** Controlled error raised when persisted output cannot satisfy the public contract. */
export class AnalysisResultValidationError extends Error {
  readonly code = 'invalid_analysis_result'

  constructor() {
    super('The copy analysis result has an invalid public structure.')
    this.name = 'AnalysisResultValidationError'
  }
}

/**
 * Validate unknown API data and convert it into the stable view model consumed
 * by copy-analysis components.
 *
 * Every current public workflow field is preserved. Unknown properties are
 * removed by the schema and validation diagnostics are not exposed to the UI.
 */
export function normalizeAnalysisResult(value: unknown): NormalizedAnalysisResult {
  const parsedResult = analysisResultSchema.safeParse(value)

  if (!parsedResult.success) {
    throw new AnalysisResultValidationError()
  }

  return buildNormalizedResult(parsedResult.data)
}

/** Validate the optional public transcription and remove unknown properties. */
export function normalizePublicTranscription(value: unknown): NormalizedTranscription | null {
  if (value === null || value === undefined) {
    return null
  }

  const parsedTranscription = publicTranscriptionSchema.safeParse(value)

  if (!parsedTranscription.success) {
    throw new AnalysisResultValidationError()
  }

  return parsedTranscription.data
}

function buildNormalizedResult(result: AnalysisResultData): NormalizedAnalysisResult {
  return {
    language: result.language,
    structure: {
      language: result.copy_structure.language,
      contentType: result.copy_structure.content_type,
      mainHook: result.copy_structure.main_hook,
      sections: result.copy_structure.sections.map((section) => ({
        type: section.section_type,
        text: section.text,
        purpose: section.purpose,
        startSeconds: section.start,
        endSeconds: section.end,
      })),
      narrativeFlow: [...result.copy_structure.narrative_flow],
      gaps: result.copy_structure.section_gaps.map((gap) => ({
        sectionType: gap.section_type,
        gapType: gap.gap_type,
        reason: gap.reason,
      })),
      summary: result.copy_structure.summary,
    },
    offer: {
      productOrSolution: result.offer_analysis.product_or_solution,
      targetAudience: result.offer_analysis.target_audience,
      coreProblem: result.offer_analysis.core_problem,
      coreDesire: result.offer_analysis.core_desire,
      mainPromise: result.offer_analysis.main_promise,
      uniqueMechanism: result.offer_analysis.unique_mechanism,
      benefits: normalizeOfferElements(result.offer_analysis.benefits),
      objections: normalizeOfferElements(result.offer_analysis.objections),
      proofElements: normalizeOfferElements(result.offer_analysis.proof_elements),
      bonuses: normalizeOfferElements(result.offer_analysis.bonuses),
      urgencyOrScarcity: normalizeOfferElements(result.offer_analysis.urgency_or_scarcity),
      callToAction: result.offer_analysis.call_to_action,
      priceOrTerms: result.offer_analysis.price_or_terms,
      summary: result.offer_analysis.summary,
    },
    persuasion: {
      dominantEmotion: result.persuasion_analysis.dominant_emotion,
      pattern: result.persuasion_analysis.persuasion_pattern,
      strengths: {
        hook: result.persuasion_analysis.hook_strength,
        promiseClarity: result.persuasion_analysis.promise_clarity,
        proof: result.persuasion_analysis.proof_strength,
        urgency: result.persuasion_analysis.urgency_strength,
        callToAction: result.persuasion_analysis.cta_strength,
      },
      signals: result.persuasion_analysis.persuasion_signals.map((signal) => ({
        name: signal.name,
        description: signal.description,
        evidence: signal.evidence,
        strength: signal.strength,
      })),
      weaknesses: result.persuasion_analysis.weaknesses.map((weakness) => ({
        issue: weakness.issue,
        impact: weakness.impact,
        evidence: weakness.evidence,
      })),
      summary: result.persuasion_analysis.summary,
    },
  }
}

function normalizeOfferElements(
  elements: AnalysisResultData['offer_analysis']['benefits'],
): readonly NormalizedOfferElement[] {
  return elements.map((element) => ({
    name: element.name,
    description: element.description,
    evidence: element.evidence,
  }))
}
