import { Badge } from '@/shared/ui/badge'

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
  const hasFindings = gaps.length > 0 || weaknesses.length > 0

  return (
    <section aria-labelledby="weakness-list-heading">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Improvement opportunities
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="weakness-list-heading">
          Gaps and weaknesses
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          Elements that may reduce clarity, credibility, desire, or conversion.
        </p>
      </div>

      {hasFindings ? (
        <div className="divide-y divide-border border-b border-border">
          {gaps.map((gap, index) => (
            <article className="py-6" key={`gap-${gap.sectionType}-${index}`}>
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant={gapVariant(gap.gapType)}>{formatLabel(gap.gapType)}</Badge>
                <p className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">
                  {formatSectionLabel(gap.sectionType)} section
                </p>
              </div>

              <h3 className="mt-3 text-body-lg font-semibold text-text">Structural gap</h3>
              <p className="mt-1 max-w-3xl text-body text-text-muted">{gap.reason}</p>
            </article>
          ))}

          {weaknesses.map((weakness, index) => (
            <WeaknessItem key={`weakness-${weakness.issue}-${index}`} weakness={weakness} />
          ))}
        </div>
      ) : (
        <p className="border-b border-border py-7 text-body text-text-muted">
          No material structural gaps or persuasive weaknesses were identified.
        </p>
      )}
    </section>
  )
}

function WeaknessItem({ weakness }: { readonly weakness: NormalizedPersuasionWeakness }) {
  return (
    <article className="py-6">
      <Badge variant="warning">Persuasion issue</Badge>
      <h3 className="mt-3 text-body-lg font-semibold text-text">{weakness.issue}</h3>
      <p className="mt-1 max-w-3xl text-body text-text-muted">{weakness.impact}</p>

      {weakness.evidence ? (
        <blockquote className="mt-4 max-w-3xl border-l-2 border-warning pl-4 text-body-sm text-text">
          {weakness.evidence}
        </blockquote>
      ) : null}
    </article>
  )
}

function gapVariant(value: NormalizedSectionGap['gapType']): 'danger' | 'warning' {
  return value === 'missing' ? 'danger' : 'warning'
}

function formatSectionLabel(value: NormalizedSectionGap['sectionType']): string {
  if (value === 'cta') return 'Call to action'
  return formatLabel(value)
}

function formatLabel(value: string): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
