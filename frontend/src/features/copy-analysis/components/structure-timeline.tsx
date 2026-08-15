import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

import type {
  NormalizedCopySection,
  NormalizedCopyStructure,
} from '../utils/normalize-analysis-result'

export interface StructureTimelineProps {
  readonly structure: NormalizedCopyStructure
}

/** Show the detected copy sections in their original narrative order. */
export function StructureTimeline({ structure }: StructureTimelineProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="copy-structure-heading" className="min-w-0">
      <div className="border-b border-border pb-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.structure.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="copy-structure-heading">
          {t('analysisResult.structure.title')}
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          {t('analysisResult.structure.description')}
        </p>
      </div>

      {structure.sections.length > 0 ? (
        <ol className="min-w-0 divide-y divide-border border-y border-border">
          {structure.sections.map((section, index) => (
            <StructureStep index={index} key={`${section.type}-${index}`} section={section} />
          ))}
        </ol>
      ) : (
        <p className="border-b border-border py-8 text-body text-text-muted">
          {t('analysisResult.structure.empty')}
        </p>
      )}
    </section>
  )
}

interface StructureStepProps {
  readonly index: number
  readonly section: NormalizedCopySection
}

function StructureStep({ index, section }: StructureStepProps) {
  const { t } = useTranslation()
  const timeRange = formatTimeRange(section.startSeconds, section.endSeconds, t)

  return (
    <li className="grid min-w-0 gap-4 py-6 sm:grid-cols-[2.5rem_minmax(10rem,0.35fr)_minmax(0,1fr)] sm:gap-6 sm:py-7">
      <span className="font-mono text-meta text-text-subtle">
        {String(index + 1).padStart(2, '0')}
      </span>

      <div className="min-w-0">
        <h3 className="text-label text-text [overflow-wrap:anywhere]">
          {formatSectionLabel(section.type, t)}
        </h3>
        <p className="mt-1 text-body-sm text-text-muted [overflow-wrap:anywhere]">
          {section.purpose}
        </p>

        {timeRange ? (
          <p className="mt-3 font-mono text-meta text-text-subtle">{timeRange}</p>
        ) : null}
      </div>

      <blockquote className="min-w-0 text-body text-text [overflow-wrap:anywhere]">
        {section.text}
      </blockquote>
    </li>
  )
}

function formatSectionLabel(value: NormalizedCopySection['type'], t: TFunction): string {
  return t(`analysisResult.sections.${value}`)
}

function formatTimeRange(
  startSeconds: number | null,
  endSeconds: number | null,
  t: TFunction,
): string | null {
  if (startSeconds === null && endSeconds === null) {
    return null
  }

  const start = formatTimestamp(startSeconds ?? 0)

  return endSeconds === null
    ? t('analysisResult.structure.fromTime', { time: start })
    : `${start}-${formatTimestamp(endSeconds)}`
}

function formatTimestamp(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safeSeconds / 60)
  const remainingSeconds = safeSeconds % 60

  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}
