import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

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
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.persuasion.scores.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="persuasion-scores-heading">
          {t('analysisResult.persuasion.scores.title')}
        </h2>
      </div>

      <table className="w-full table-fixed border-b border-border">
        <tbody className="divide-y divide-border">
          {STRENGTH_ITEMS.map(([labelKey, key]) => (
            <StrengthRow key={key} label={t(labelKey)} value={strengths[key]} />
          ))}
        </tbody>
      </table>
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
    <tr>
      <th
        className="min-w-0 py-4 pr-3 text-left text-body font-normal text-text [overflow-wrap:anywhere] sm:pr-6"
        scope="row"
      >
        {label}
      </th>
      <td className="w-20 py-4 text-right sm:w-24">
        <span aria-hidden="true" className="inline-flex w-[4.25rem] justify-end gap-1">
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
      </td>
      <td className="w-20 py-4 pl-3 text-right text-label font-medium text-text sm:w-24 sm:pl-4">
        {formatStrength(level, t)}
      </td>
    </tr>
  )
}

function isFilledSegment(level: PersuasionStrengthLevel, segment: number): boolean {
  const filledSegments = level === 'high' ? 3 : level === 'medium' ? 2 : level === 'low' ? 1 : 0

  return segment <= filledSegments
}

function formatStrength(level: PersuasionStrengthLevel, t: TFunction): string {
  if (level !== 'unknown') {
    return t(`analysisResult.persuasion.strength.${level}`)
  }

  return t('analysisResult.persuasion.strength.notRated')
}
