import type { NormalizedCopyAnalysisJobResult } from '../hooks/use-job-result'
import { AnalysisOverview } from './analysis-overview'
import { OfferSummary } from './offer-summary'
import { PersuasionScores } from './persuasion-scores'
import { PersuasionSignals } from './persuasion-signals'
import { StructureTimeline } from './structure-timeline'
import { TranscriptViewer } from './transcript-viewer'
import { WeaknessList } from './weakness-list'

export interface AnalysisResultProps {
  readonly result: NormalizedCopyAnalysisJobResult
}

/** Compose the complete copy-analysis reading from normalized public data. */
export function AnalysisResult({ result }: AnalysisResultProps) {
  const { analysis, transcription } = result

  return (
    <article className="min-w-0 space-y-16 sm:space-y-20">
      <AnalysisOverview analysis={analysis} />

      <StructureTimeline structure={analysis.structure} />

      <OfferSummary offer={analysis.offer} />

      <div className="min-w-0 space-y-12 border-t border-border pt-12 sm:space-y-16 sm:pt-16">
        <PersuasionScores strengths={analysis.persuasion.strengths} />
        <PersuasionSignals signals={analysis.persuasion.signals} />
      </div>

      <WeaknessList gaps={analysis.structure.gaps} weaknesses={analysis.persuasion.weaknesses} />

      <TranscriptViewer transcription={transcription} />
    </article>
  )
}
