import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

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
            <li className="min-w-0" key={`${signal.name}-${index}`}>
              <details className="group min-w-0">
                <summary className="flex min-w-0 cursor-pointer list-none items-center justify-between gap-5 py-5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus [&::-webkit-details-marker]:hidden">
                  <span className="min-w-0 text-body-lg font-semibold text-text [overflow-wrap:anywhere]">
                    {signal.name}
                  </span>

                  <span className="flex shrink-0 items-center gap-4">
                    <span className="text-label font-medium text-text-muted">
                      {formatStrengthLabel(signal.strength.level, t)}
                    </span>
                    <ChevronIcon />
                  </span>
                </summary>

                <div className="min-w-0 pb-6 pr-8 sm:pr-12">
                  <p className="max-w-3xl text-body text-text-muted [overflow-wrap:anywhere]">
                    {signal.description}
                  </p>

                  {signal.evidence ? (
                    <blockquote className="mt-4 max-w-3xl border-l-2 border-action pl-4 text-body-sm text-text [overflow-wrap:anywhere]">
                      {signal.evidence}
                    </blockquote>
                  ) : null}
                </div>
              </details>
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

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 transition-transform duration-(--duration-fast) group-open:rotate-180"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="m4 6 4 4 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
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
