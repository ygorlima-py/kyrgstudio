import { Badge } from '@/shared/ui/badge'
import { cn } from '@/shared/utils/class-names'

import type { NormalizedPersuasionStrengths } from '../utils/normalize-analysis-result'

const STRENGTH_ITEMS = [
  ['Hook', 'hook'],
  ['Promise clarity', 'promiseClarity'],
  ['Proof', 'proof'],
  ['Urgency', 'urgency'],
  ['Call to action', 'callToAction'],
] as const satisfies readonly (readonly [string, keyof NormalizedPersuasionStrengths])[]

type StrengthLevel = 'low' | 'medium' | 'high' | 'unknown'

export interface PersuasionScoresProps {
  readonly strengths: NormalizedPersuasionStrengths
}

/** Display qualitative persuasion ratings without inventing numerical scores. */
export function PersuasionScores({ strengths }: PersuasionScoresProps) {
  return (
    <section aria-labelledby="persuasion-scores-heading">
      <div>
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Persuasion diagnosis
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="persuasion-scores-heading">
          Strength by element
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          Qualitative ratings found by the analysis. These are not numerical conversion scores.
        </p>
      </div>

      <dl className="mt-6 divide-y divide-border border-y border-border">
        {STRENGTH_ITEMS.map(([label, key]) => (
          <StrengthRow key={key} label={label} value={strengths[key]} />
        ))}
      </dl>
    </section>
  )
}

function StrengthRow({ label, value }: { readonly label: string; readonly value: string | null }) {
  const level = normalizeStrength(value)

  return (
    <div className="flex items-center justify-between gap-6 py-4">
      <dt className="text-body text-text">{label}</dt>
      <dd className="flex items-center gap-3">
        <span aria-hidden="true" className="flex gap-1">
          {[1, 2, 3].map((segment) => (
            <span
              className={cn(
                'h-1.5 w-5 rounded-pill bg-surface-muted',
                isFilledSegment(level, segment) && level === 'low' && 'bg-danger',
                isFilledSegment(level, segment) && level === 'medium' && 'bg-warning',
                isFilledSegment(level, segment) && level === 'high' && 'bg-success',
              )}
              key={segment}
            />
          ))}
        </span>

        <Badge variant={strengthBadgeVariant(level)}>{formatStrength(value)}</Badge>
      </dd>
    </div>
  )
}

function normalizeStrength(value: string | null): StrengthLevel {
  const normalizedValue = value?.trim().toLowerCase()

  return normalizedValue === 'low' || normalizedValue === 'medium' || normalizedValue === 'high'
    ? normalizedValue
    : 'unknown'
}

function isFilledSegment(level: StrengthLevel, segment: number): boolean {
  const filledSegments = level === 'high' ? 3 : level === 'medium' ? 2 : level === 'low' ? 1 : 0

  return segment <= filledSegments
}

function strengthBadgeVariant(level: StrengthLevel): 'danger' | 'warning' | 'success' | 'neutral' {
  if (level === 'high') return 'success'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'danger'
  return 'neutral'
}

function formatStrength(value: string | null): string {
  if (!value) return 'Not rated'

  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
