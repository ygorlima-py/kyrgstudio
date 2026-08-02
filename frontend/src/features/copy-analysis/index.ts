export { jobResultQueryKey, useJobResult } from './hooks/use-job-result'
export { AnalysisOverview } from './components/analysis-overview'
export { AnalysisResult } from './components/analysis-result'
export { NarrativeFlow } from './components/narrative-flow'
export { OfferSummary } from './components/offer-summary'
export { PersuasionScores } from './components/persuasion-scores'
export { PersuasionSignals } from './components/persuasion-signals'
export { StructureTimeline } from './components/structure-timeline'
export { TranscriptViewer } from './components/transcript-viewer'
export { WeaknessList } from './components/weakness-list'
export {
  AnalysisResultValidationError,
  normalizeAnalysisResult,
  normalizePublicTranscription,
} from './utils/normalize-analysis-result'

export type { JobResultQueryError, NormalizedCopyAnalysisJobResult } from './hooks/use-job-result'
export type { AnalysisOverviewProps } from './components/analysis-overview'
export type { AnalysisResultProps } from './components/analysis-result'
export type { NarrativeFlowProps } from './components/narrative-flow'
export type { OfferSummaryProps } from './components/offer-summary'
export type { PersuasionScoresProps } from './components/persuasion-scores'
export type { PersuasionSignalsProps } from './components/persuasion-signals'
export type { StructureTimelineProps } from './components/structure-timeline'
export type { TranscriptViewerProps } from './components/transcript-viewer'
export type { WeaknessListProps } from './components/weakness-list'
export type {
  NormalizedAnalysisResult,
  NormalizedCopySection,
  NormalizedCopyStructure,
  NormalizedOfferAnalysis,
  NormalizedOfferElement,
  NormalizedPersuasionAnalysis,
  NormalizedPersuasionSignal,
  NormalizedPersuasionStrengths,
  NormalizedPersuasionWeakness,
  NormalizedSectionGap,
  NormalizedTranscription,
} from './utils/normalize-analysis-result'
