import { Badge } from '@/shared/ui/badge'

import type { NormalizedPersuasionSignal } from '../utils/normalize-analysis-result'

export interface PersuasionSignalsProps {
  readonly signals: readonly NormalizedPersuasionSignal[]
}

/** Explain the persuasive techniques detected and the evidence supporting them. */
export function PersuasionSignals({ signals }: PersuasionSignalsProps) {
  return (
    <section aria-labelledby="persuasion-signals-heading">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Detected techniques
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="persuasion-signals-heading">
          Persuasion signals
        </h2>
      </div>

      {signals.length > 0 ? (
        <ul className="divide-y divide-border border-b border-border">
          {signals.map((signal, index) => (
            <li className="py-6" key={`${signal.name}-${index}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-body-lg font-semibold text-text">{signal.name}</h3>
                <Badge variant={strengthVariant(signal.strength)}>
                  {formatLabel(signal.strength)}
                </Badge>
              </div>

              <p className="mt-2 max-w-3xl text-body text-text-muted">{signal.description}</p>

              {signal.evidence ? (
                <blockquote className="mt-4 max-w-3xl border-l-2 border-action pl-4 text-body-sm text-text">
                  {signal.evidence}
                </blockquote>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="border-b border-border py-7 text-body text-text-muted">
          No distinct persuasion signals were identified.
        </p>
      )}
    </section>
  )
}

function strengthVariant(value: string): 'danger' | 'warning' | 'success' | 'neutral' {
  const strength = value.trim().toLowerCase()

  if (strength === 'high') return 'success'
  if (strength === 'medium') return 'warning'
  if (strength === 'low') return 'danger'
  return 'neutral'
}

function formatLabel(value: string): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
