import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'

import type { NormalizedAdaptedScriptSection } from '../utils/normalize-adaptation-result'

export interface ScriptSectionsProps {
  readonly sections: readonly NormalizedAdaptedScriptSection[]
}

/** Present the generated script architecture as a compact, expandable list. */
export function ScriptSections({ sections }: ScriptSectionsProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="adapted-sections-heading">
      <header className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('adaptationResult.scriptSections.eyebrow')}
        </p>
        <h2 className="mt-2 font-heading text-heading-3 text-text" id="adapted-sections-heading">
          {t('adaptationResult.scriptSections.title')}
        </h2>
        <p className="mt-2 max-w-3xl text-body text-text-muted">
          {t('adaptationResult.scriptSections.description')}
        </p>
      </header>

      {sections.length > 0 ? (
        <div className="divide-y divide-border border-b border-border">
          {sections.map((section) => (
            <ScriptSection key={`${section.order}-${section.type}`} section={section} />
          ))}
        </div>
      ) : (
        <div className="border-b border-border py-8">
          <p className="text-body text-text-muted">{t('adaptationResult.scriptSections.empty')}</p>
        </div>
      )}
    </section>
  )
}

interface ScriptSectionProps {
  readonly section: NormalizedAdaptedScriptSection
}

function ScriptSection({ section }: ScriptSectionProps) {
  const { t } = useTranslation()

  return (
    <details className="group">
      <summary className="grid min-h-20 cursor-pointer list-none grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-4 py-5 marker:hidden sm:grid-cols-[3rem_minmax(10rem,0.35fr)_minmax(0,1fr)_auto] sm:gap-6 [&::-webkit-details-marker]:hidden">
        <span className="font-mono text-meta text-text-subtle">
          {String(section.order).padStart(2, '0')}
        </span>

        <div>
          <h3 className="text-label text-text">{t(`analysisResult.sections.${section.type}`)}</h3>
          <p className="mt-1 font-mono text-meta text-text-subtle">
            {formatDuration(section.estimatedDurationSeconds, t)}
          </p>
        </div>

        <p className="col-span-3 row-start-2 line-clamp-2 text-body-sm text-text-muted sm:col-span-1 sm:col-start-3 sm:row-start-1">
          {section.purpose}
        </p>

        <span className="col-start-3 row-start-1 flex items-center justify-end gap-3 sm:col-start-4">
          <Badge variant={section.missingProof ? 'warning' : 'neutral'}>
            {section.adaptationMode === 'adapted_from_reference'
              ? t('adaptationResult.scriptSections.adapted')
              : t('adaptationResult.scriptSections.original')}
          </Badge>
          <ChevronIcon />
        </span>
      </summary>

      <div className="grid gap-6 border-t border-border bg-surface px-5 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
            {t('adaptationResult.scriptSections.sectionCopy')}
          </p>
          <p className="mt-3 whitespace-pre-wrap text-body leading-7 text-text">{section.text}</p>
        </div>

        <dl className="divide-y divide-border border-y border-border text-body-sm">
          <SectionDetail
            label={t('adaptationResult.scriptSections.purpose')}
            value={section.purpose}
          />
          <SectionDetail
            label={t('adaptationResult.scriptSections.reference')}
            value={
              section.sourceReferenceSectionType === null
                ? t('adaptationResult.scriptSections.noReference')
                : t(`analysisResult.sections.${section.sourceReferenceSectionType}`)
            }
          />
          <SectionDetail
            label={t('adaptationResult.scriptSections.proof')}
            value={
              section.missingProof
                ? t('adaptationResult.scriptSections.requiresProof')
                : (section.proofUsed ?? t('adaptationResult.scriptSections.noProof'))
            }
          />
          <SectionDetail
            label={t('adaptationResult.scriptSections.transition')}
            value={section.transitionHint ?? t('adaptationResult.scriptSections.noTransition')}
          />
          <SectionDetail
            label={t('adaptationResult.scriptSections.timing')}
            value={`${formatTimeRange(section.startSeconds, section.endSeconds, t)} · ${t(
              'adaptationResult.scriptSections.wordCount',
              { count: section.wordCount },
            )}`}
          />
        </dl>
      </div>
    </details>
  )
}

interface SectionDetailProps {
  readonly label: string
  readonly value: string
}

function SectionDetail({ label, value }: SectionDetailProps) {
  return (
    <div className="py-3 first:pt-0 last:pb-0">
      <dt className="font-mono text-meta uppercase tracking-[0.08em] text-text-subtle">{label}</dt>
      <dd className="mt-1 text-body-sm text-text-muted">{value}</dd>
    </div>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 text-text-subtle transition-transform duration-(--duration-fast) group-open:rotate-180"
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

function formatDuration(seconds: number | null, t: TFunction): string {
  if (seconds === null) {
    return t('adaptationResult.scriptSections.durationUnavailable')
  }

  return t('adaptationResult.scriptSections.seconds', {
    count: Math.max(0, Math.round(seconds)),
  })
}

function formatTimeRange(
  startSeconds: number | null,
  endSeconds: number | null,
  t: TFunction,
): string {
  if (startSeconds === null && endSeconds === null) {
    return t('adaptationResult.scriptSections.timingUnavailable')
  }

  const start = formatTimestamp(startSeconds ?? 0)

  return endSeconds === null
    ? t('adaptationResult.scriptSections.fromTime', { time: start })
    : `${start}-${formatTimestamp(endSeconds)}`
}

function formatTimestamp(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  const remainingSeconds = safeSeconds % 60

  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}
