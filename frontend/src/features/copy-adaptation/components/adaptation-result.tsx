import type { NormalizedAdaptationResult } from '../utils/normalize-adaptation-result'
import { AdaptationValidation } from './adaptation-validation'
import { MissingProofs } from './missing-proofs'
import { ReferenceAnalysis } from './reference-analysis'
import { ScriptEditor } from './script-editor'
import { ScriptSections } from './script-sections'

export interface AdaptationResultProps {
  readonly result: NormalizedAdaptationResult
}

/** Compose the complete copy-adaptation workspace from normalized public data. */
export function AdaptationResult({ result }: AdaptationResultProps) {
  return (
    <article className="space-y-14 sm:space-y-16 lg:space-y-20">
      <ScriptEditor script={result.script} />

      <ScriptSections sections={result.script.sections} />

      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1.2fr)_minmax(19rem,0.8fr)]">
        <AdaptationValidation validation={result.validation} />
        <MissingProofs proofs={result.missingProofs} />
      </div>

      <ReferenceAnalysis analysis={result.referenceAnalysis} />
    </article>
  )
}
