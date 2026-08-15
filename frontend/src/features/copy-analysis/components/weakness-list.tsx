import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import type {
  NormalizedPersuasionWeakness,
  NormalizedSectionGap,
} from '../utils/normalize-analysis-result'

export interface WeaknessListProps {
  readonly gaps: readonly NormalizedSectionGap[]
  readonly weaknesses: readonly NormalizedPersuasionWeakness[]
}

/** Combine structural gaps and persuasive risks into one actionable diagnosis. */
export function WeaknessList({ gaps, weaknesses }: WeaknessListProps) {
  const { t } = useTranslation()
  const hasFindings = gaps.length > 0 || weaknesses.length > 0

  return (
    <section aria-labelledby="weakness-list-heading">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.weaknesses.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="weakness-list-heading">
          {t('analysisResult.weaknesses.title')}
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          {t('analysisResult.weaknesses.description')}
        </p>
      </div>

      {hasFindings ? (
        <div className="divide-y divide-border border-b border-border">
          {gaps.map((gap, index) => (
            <article className="py-6" key={`gap-${gap.sectionType}-${index}`}>
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono text-meta uppercase tracking-[0.08em] text-action">
                  {formatGapType(gap.gapType, t)}
                </span>
                <p className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">
                  {t('analysisResult.weaknesses.sectionLabel', {
                    section: formatSectionLabel(gap.sectionType, t),
                  })}
                </p>
              </div>

              <h3 className="mt-3 text-body-lg font-semibold text-text">
                {t('analysisResult.weaknesses.structuralGap')}
              </h3>
              <p className="mt-1 max-w-3xl text-body text-text-muted [overflow-wrap:anywhere]">
                {gap.reason}
              </p>
            </article>
          ))}

          {weaknesses.map((weakness, index) => (
            <WeaknessItem key={`weakness-${weakness.issue}-${index}`} weakness={weakness} />
          ))}
        </div>
      ) : (
        <p className="border-b border-border py-7 text-body text-text-muted">
          {t('analysisResult.weaknesses.empty')}
        </p>
      )}
    </section>
  )
}

function WeaknessItem({ weakness }: { readonly weakness: NormalizedPersuasionWeakness }) {
  const { t } = useTranslation()

  return (
    <article className="py-6">
      <p className="font-mono text-meta uppercase tracking-[0.08em] text-action">
        {t('analysisResult.weaknesses.persuasionIssue')}
      </p>
      <h3 className="mt-3 text-body-lg font-semibold text-text [overflow-wrap:anywhere]">
        {weakness.issue}
      </h3>
      <p className="mt-1 max-w-3xl text-body text-text-muted [overflow-wrap:anywhere]">
        {weakness.impact}
      </p>

      {weakness.evidence ? (
        <blockquote className="mt-4 max-w-3xl border-l-2 border-warning pl-4 text-body-sm text-text [overflow-wrap:anywhere]">
          {weakness.evidence}
        </blockquote>
      ) : null}
    </article>
  )
}

function formatGapType(value: NormalizedSectionGap['gapType'], t: TFunction): string {
  return t(`analysisResult.weaknesses.gapTypes.${value}`)
}

function formatSectionLabel(value: NormalizedSectionGap['sectionType'], t: TFunction): string {
  return t(`analysisResult.sections.${value}`)
}
