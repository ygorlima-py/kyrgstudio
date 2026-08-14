import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'

import type { NormalizedPersuasionSignal } from '../utils/normalize-analysis-result'

export interface PersuasionSignalsProps {
  readonly signals: readonly NormalizedPersuasionSignal[]
}

/** Explain the persuasive techniques detected and the evidence supporting them. */
export function PersuasionSignals({ signals }: PersuasionSignalsProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="persuasion-signals-heading" className="min-w-0">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.persuasion.signals.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="persuasion-signals-heading">
          {t('analysisResult.persuasion.signals.title')}
        </h2>
      </div>

      {signals.length > 0 ? (
        <ul className="divide-y divide-border border-b border-border">
          {signals.map((signal, index) => (
            <li className="py-6" key={`${signal.name}-${index}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-body-lg font-semibold text-text">{signal.name}</h3>
                <Badge variant={strengthVariant(signal.strength.level)}>
                  {formatStrengthLabel(signal.strength.level, t)}
                </Badge>
              </div>

              <p className="mt-2 max-w-3xl break-words text-body text-text-muted">
                {signal.description}
              </p>

              {signal.evidence ? (
                <blockquote className="mt-4 max-w-3xl break-words border-l-2 border-action pl-4 text-body-sm text-text">
                  {signal.evidence}
                </blockquote>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="border-b border-border py-7 text-body text-text-muted">
          {t('analysisResult.persuasion.signals.empty')}
        </p>
      )}
    </section>
  )
}

function strengthVariant(
  strength: 'low' | 'medium' | 'high' | 'unknown',
): 'danger' | 'warning' | 'success' | 'neutral' {
  if (strength === 'high') return 'success'
  if (strength === 'medium') return 'warning'
  if (strength === 'low') return 'danger'
  return 'neutral'
}

function formatStrengthLabel(
  strength: 'low' | 'medium' | 'high' | 'unknown',
  t: TFunction,
): string {
  if (strength !== 'unknown') {
    return t(`analysisResult.persuasion.strength.${strength}`)
  }

  return t('analysisResult.persuasion.strength.notRated')
}
