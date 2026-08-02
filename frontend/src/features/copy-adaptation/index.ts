export { AdaptationResult } from './components/adaptation-result'
export { AdaptationValidation } from './components/adaptation-validation'
export { MissingProofs } from './components/missing-proofs'
export { ReferenceAnalysis } from './components/reference-analysis'
export { ScriptEditor } from './components/script-editor'
export { ScriptSections } from './components/script-sections'
export { adaptationJobResultQueryKey, useAdaptationResult } from './hooks/use-adaptation-result'
export {
  AdaptationResultValidationError,
  normalizeAdaptationResult,
} from './utils/normalize-adaptation-result'

export type { AdaptationResultProps } from './components/adaptation-result'
export type { AdaptationValidationProps } from './components/adaptation-validation'
export type { MissingProofsProps } from './components/missing-proofs'
export type { ReferenceAnalysisProps } from './components/reference-analysis'
export type { ScriptEditorProps } from './components/script-editor'
export type { ScriptSectionsProps } from './components/script-sections'
export type { AdaptationJobResultQueryError } from './hooks/use-adaptation-result'
export type {
  NormalizedAdaptationResult,
  NormalizedAdaptationValidation,
  NormalizedAdaptationValidationIssue,
  NormalizedAdaptedScript,
  NormalizedAdaptedScriptSection,
} from './utils/normalize-adaptation-result'
