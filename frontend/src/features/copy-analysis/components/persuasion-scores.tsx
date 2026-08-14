import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'
import { cn } from '@/shared/utils/class-names'

import type {
  NormalizedPersuasionStrength,
  NormalizedPersuasionStrengths,
  PersuasionStrengthLevel,
} from '../utils/normalize-analysis-result'

const STRENGTH_ITEMS = [
  ['analysisResult.persuasion.scores.items.hook', 'hook'],
  ['analysisResult.persuasion.scores.items.promiseClarity', 'promiseClarity'],
  ['analysisResult.persuasion.scores.items.proof', 'proof'],
  ['analysisResult.persuasion.scores.items.urgency', 'urgency'],
  ['analysisResult.persuasion.scores.items.callToAction', 'callToAction'],
] as const satisfies readonly (readonly [string, keyof NormalizedPersuasionStrengths])[]

export interface PersuasionScoresProps {
  readonly strengths: NormalizedPersuasionStrengths
}

/** Display qualitative persuasion ratings without inventing numerical scores. */
export function PersuasionScores({ strengths }: PersuasionScoresProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="persuasion-scores-heading" className="min-w-0">
      <div>
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.persuasion.scores.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="persuasion-scores-heading">
          {t('analysisResult.persuasion.scores.title')}
        </h2>
      </div>

      <dl className="mt-6 divide-y divide-border border-y border-border">
        {STRENGTH_ITEMS.map(([labelKey, key]) => (
          <StrengthRow key={key} label={t(labelKey)} value={strengths[key]} />
        ))}
      </dl>
    </section>
  )
}

function StrengthRow({
  label,
  value,
}: {
  readonly label: string
  readonly value: NormalizedPersuasionStrength
}) {
  const { t } = useTranslation()
  const { level } = value

  return (
    <div className="grid min-w-0 gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(10rem,auto)] sm:items-start sm:gap-6">
      <dt className="min-w-0 text-body text-text">{label}</dt>
      <dd className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-3 sm:justify-end">
          <span aria-hidden="true" className="flex shrink-0 gap-1">
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

          <Badge variant={strengthBadgeVariant(level)}>{formatStrength(level, t)}</Badge>
        </div>

        {value.explanation ? (
          <p className="mt-2 max-w-full break-words text-body-sm text-text-muted sm:text-right">
            {value.explanation}
          </p>
        ) : null}
      </dd>
    </div>
  )
}

function isFilledSegment(level: PersuasionStrengthLevel, segment: number): boolean {
  const filledSegments = level === 'high' ? 3 : level === 'medium' ? 2 : level === 'low' ? 1 : 0

  return segment <= filledSegments
}

function strengthBadgeVariant(
  level: PersuasionStrengthLevel,
): 'danger' | 'warning' | 'success' | 'neutral' {
  if (level === 'high') return 'success'
  if (level === 'medium') return 'warning'
  if (level === 'low') return 'danger'
  return 'neutral'
}

function formatStrength(level: PersuasionStrengthLevel, t: TFunction): string {
  if (level !== 'unknown') {
    return t(`analysisResult.persuasion.strength.${level}`)
  }

  return t('analysisResult.persuasion.strength.notRated')
}
