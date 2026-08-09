import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import type { NormalizedAnalysisResult } from '../utils/normalize-analysis-result'

export interface AnalysisOverviewProps {
  readonly analysis: NormalizedAnalysisResult
}

/** Present the strategic reading of a copy without exposing its raw payload. */
export function AnalysisOverview({ analysis }: AnalysisOverviewProps) {
  const { t } = useTranslation()
  const { persuasion, structure } = analysis

  return (
    <section
      aria-labelledby="analysis-overview-heading"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <div className="border-b border-border px-5 py-6 sm:px-8 sm:py-8">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.overview.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="analysis-overview-heading">
          {t('analysisResult.overview.title')}
        </h2>

        <p className="mt-3 max-w-3xl text-body text-text-muted">{structure.summary}</p>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1.5fr)_minmax(17rem,0.75fr)]">
        <div className="px-5 py-6 sm:px-8 sm:py-8">
          <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
            {t('analysisResult.overview.mainHook')}
          </p>

          {structure.mainHook ? (
            <blockquote className="mt-4 border-l-2 border-action pl-5 font-heading text-heading-3 text-text">
              {structure.mainHook}
            </blockquote>
          ) : (
            <p className="mt-3 text-body text-text-muted">
              {t('analysisResult.overview.noMainHook')}
            </p>
          )}
        </div>

        <dl className="grid grid-cols-2 border-t border-border lg:grid-cols-1 lg:border-t-0 lg:border-l">
          <OverviewDetail
            label={t('analysisResult.overview.details.contentType')}
            value={formatDescriptor(structure.contentType, t)}
          />
          <OverviewDetail
            label={t('analysisResult.overview.details.language')}
            value={
              analysis.language ?? structure.language ?? t('analysisResult.common.notIdentified')
            }
          />
          <OverviewDetail
            label={t('analysisResult.overview.details.dominantEmotion')}
            value={persuasion.dominantEmotion ?? t('analysisResult.common.notIdentified')}
          />
          <OverviewDetail
            label={t('analysisResult.overview.details.persuasionPattern')}
            value={persuasion.pattern ?? t('analysisResult.common.notIdentified')}
          />
        </dl>
      </div>
    </section>
  )
}

function OverviewDetail({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="border-b border-border px-5 py-4 last:border-b-0 odd:border-r sm:px-6 lg:odd:border-r-0">
      <dt className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm font-medium text-text">{value}</dd>
    </div>
  )
}

function formatDescriptor(value: string, t: TFunction): string {
  const normalizedValue = value.trim().replaceAll(/[_-]+/g, ' ')
  const descriptorKey = normalizedValue.toLowerCase()

  if (descriptorKey === 'video') {
    return t('analysisResult.contentTypes.video')
  }

  if (descriptorKey === 'audio') {
    return t('analysisResult.contentTypes.audio')
  }

  return normalizedValue.charAt(0).toUpperCase() + normalizedValue.slice(1)
}
