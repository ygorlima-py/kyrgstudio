import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import type { NormalizedAnalysisResult } from '../utils/normalize-analysis-result'

export interface AnalysisOverviewProps {
  readonly analysis: NormalizedAnalysisResult
}

/** Present the strategic reading of a copy without exposing its raw payload. */
export function AnalysisOverview({ analysis }: AnalysisOverviewProps) {
  const { i18n, t } = useTranslation()
  const { structure } = analysis
  const language = analysis.language ?? structure.language

  return (
    <section aria-labelledby="analysis-overview-heading" className="min-w-0 border-y border-border">
      <div className="border-b border-border py-8 sm:py-10">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.overview.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="analysis-overview-heading">
          {t('analysisResult.overview.title')}
        </h2>

        <p className="mt-4 max-w-3xl break-words text-body-lg leading-relaxed text-text-muted">
          {structure.summary}
        </p>
      </div>

      <div className="grid min-w-0 lg:grid-cols-[minmax(0,1fr)_minmax(14rem,0.4fr)]">
        <div className="min-w-0 border-b border-border py-7 lg:border-b-0 lg:border-r lg:py-8 lg:pr-10">
          <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
            {t('analysisResult.overview.mainHook')}
          </p>

          {structure.mainHook ? (
            <blockquote className="mt-4 max-w-3xl border-l-2 border-action pl-5 text-body-lg font-medium leading-relaxed text-text [overflow-wrap:anywhere]">
              {structure.mainHook}
            </blockquote>
          ) : (
            <p className="mt-3 text-body text-text-muted">
              {t('analysisResult.overview.noMainHook')}
            </p>
          )}
        </div>

        <dl className="grid min-w-0 grid-cols-2 lg:grid-cols-1">
          <OverviewDetail
            label={t('analysisResult.overview.details.contentType')}
            value={formatDescriptor(structure.contentType, t)}
          />
          <OverviewDetail
            label={t('analysisResult.overview.details.language')}
            value={formatLanguage(language, i18n.resolvedLanguage, t)}
          />
        </dl>
      </div>
    </section>
  )
}

function OverviewDetail({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div className="min-w-0 max-w-full border-b border-border py-5 last:border-b-0 odd:border-r lg:odd:border-r-0 lg:py-6">
      <dt className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">{label}</dt>
      <dd className="mt-1 min-w-0 max-w-full text-body-sm font-medium text-text [overflow-wrap:anywhere]">
        {value}
      </dd>
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

function formatLanguage(value: string | null, locale: string | undefined, t: TFunction): string {
  if (!value) {
    return t('analysisResult.common.notIdentified')
  }

  const languageCode = value.trim().toLowerCase().split(/[-_]/, 1)[0]

  if (!languageCode || languageCode.length > 3) {
    return value
  }

  try {
    return new Intl.DisplayNames([locale ?? 'en'], { type: 'language' }).of(languageCode) ?? value
  } catch {
    return value
  }
}
