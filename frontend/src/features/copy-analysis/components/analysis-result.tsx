import type { NormalizedCopyAnalysisJobResult } from '../hooks/use-job-result'
import { AnalysisOverview } from './analysis-overview'
import { NarrativeFlow } from './narrative-flow'
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
    <article className="space-y-14 sm:space-y-16 lg:space-y-20">
      <AnalysisOverview analysis={analysis} />

      <StructureTimeline structure={analysis.structure} />

      <NarrativeFlow steps={analysis.structure.narrativeFlow} />

      <OfferSummary offer={analysis.offer} />

      <div className="grid gap-14 border-t border-border pt-14 sm:gap-16 sm:pt-16 xl:grid-cols-[minmax(18rem,0.7fr)_minmax(0,1.3fr)] xl:gap-16">
        <PersuasionScores strengths={analysis.persuasion.strengths} />
        <PersuasionSignals signals={analysis.persuasion.signals} />
      </div>

      <WeaknessList gaps={analysis.structure.gaps} weaknesses={analysis.persuasion.weaknesses} />

      <TranscriptViewer transcription={transcription} />
    </article>
  )
}
