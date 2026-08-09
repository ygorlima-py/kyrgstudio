import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'

import type {
  NormalizedAnalysisResult,
} from '@/features/copy-analysis/utils/normalize-analysis-result'

export interface ReferenceAnalysisProps {
  readonly analysis: NormalizedAnalysisResult
}

/** Keep the source strategy available without mixing it with the adapted copy. */
export function ReferenceAnalysis({ analysis }: ReferenceAnalysisProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="reference-analysis-heading">
      <details className="group overflow-hidden rounded-lg border border-border bg-surface">
        <summary className="grid cursor-pointer list-none gap-4 px-5 py-6 marker:hidden sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-8 sm:py-7 [&::-webkit-details-marker]:hidden">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
                {t('adaptationResult.referenceAnalysis.eyebrow')}
              </p>
              <Badge variant="neutral">
                {t('adaptationResult.referenceAnalysis.referenceOnly')}
              </Badge>
            </div>
            <h2
              className="mt-2 font-heading text-heading-3 text-text"
              id="reference-analysis-heading"
            >
              {t('adaptationResult.referenceAnalysis.title')}
            </h2>
            <p className="mt-2 line-clamp-2 max-w-3xl text-body-sm text-text-muted">
              {analysis.structure.summary}
            </p>
          </div>

          <span className="flex items-center gap-2 text-label text-text-muted">
            {t('adaptationResult.referenceAnalysis.viewReference')}
            <ChevronIcon />
          </span>
        </summary>

        <div className="border-t border-border">
          <dl className="grid grid-cols-2 gap-px border-b border-border bg-border lg:grid-cols-4">
            <ReferenceMetric
              label={t('adaptationResult.referenceAnalysis.contentType')}
              value={analysis.structure.contentType}
            />
            <ReferenceMetric
              label={t('adaptationResult.referenceAnalysis.language')}
              value={
                analysis.language ??
                analysis.structure.language ??
                t('analysisResult.common.notIdentified')
              }
            />
            <ReferenceMetric
              label={t('adaptationResult.referenceAnalysis.persuasionPattern')}
              value={analysis.persuasion.pattern ?? t('analysisResult.common.notIdentified')}
            />
            <ReferenceMetric
              label={t('adaptationResult.referenceAnalysis.dominantEmotion')}
              value={
                analysis.persuasion.dominantEmotion ?? t('analysisResult.common.notIdentified')
              }
            />
          </dl>

          <div className="grid lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)]">
            <div className="px-5 py-6 sm:px-8 sm:py-8">
              <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
                {t('adaptationResult.referenceAnalysis.referenceHook')}
              </p>
              {analysis.structure.mainHook ? (
                <blockquote className="mt-4 border-l-2 border-action pl-5 font-heading text-heading-3 text-text">
                  {analysis.structure.mainHook}
                </blockquote>
              ) : (
                <p className="mt-3 text-body text-text-muted">
                  {t('adaptationResult.referenceAnalysis.noDominantHook')}
                </p>
              )}
            </div>

            <div className="border-t border-border px-5 py-6 sm:px-8 lg:border-t-0 lg:border-l lg:px-6 lg:py-8">
              <ReferenceSummary
                label={t('adaptationResult.referenceAnalysis.offerReading')}
                value={analysis.offer.summary}
              />
              <ReferenceSummary
                label={t('adaptationResult.referenceAnalysis.persuasionReading')}
                value={analysis.persuasion.summary}
              />
            </div>
          </div>

          <div className="border-t border-border px-5 py-6 sm:px-8">
            <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
              {t('adaptationResult.referenceAnalysis.referenceSequence')}
            </p>
            {analysis.structure.sections.length > 0 ? (
              <ol className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
                {analysis.structure.sections.map((section, index) => (
                  <li
                    className="grid grid-cols-[2rem_minmax(0,1fr)] items-baseline gap-2 border-b border-border pb-3"
                    key={`${section.type}-${index}`}
                  >
                    <span className="font-mono text-meta text-text-subtle">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="text-body-sm font-medium text-text">
                      {t(`analysisResult.sections.${section.type}`)}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-body text-text-muted">
                {t('adaptationResult.referenceAnalysis.noSequence')}
              </p>
            )}
          </div>

          <footer className="border-t border-border bg-surface-muted/45 px-5 py-4 sm:px-8">
            <p className="text-body-sm text-text-muted">
              {t('adaptationResult.referenceAnalysis.footer')}
            </p>
          </footer>
        </div>
      </details>
    </section>
  )
}

interface ReferenceMetricProps {
  readonly label: string
  readonly value: string
}

function ReferenceMetric({ label, value }: ReferenceMetricProps) {
  const { t } = useTranslation()

  return (
    <div className="bg-surface px-5 py-4 sm:px-6">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm font-medium text-text">{formatLabel(value, t)}</dd>
    </div>
  )
}

interface ReferenceSummaryProps {
  readonly label: string
  readonly value: string
}

function ReferenceSummary({ label, value }: ReferenceSummaryProps) {
  return (
    <section className="border-b border-border py-5 first:pt-0 last:border-b-0 last:pb-0">
      <h3 className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</h3>
      <p className="mt-2 text-body-sm text-text-muted">{value}</p>
    </section>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 transition-transform duration-(--duration-fast) group-open:rotate-180"
      fill="none"
      viewBox="0 0 20 20"
    >
      <path
        d="m5 7.5 5 5 5-5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}

function formatLabel(value: string, t: TFunction): string {
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
