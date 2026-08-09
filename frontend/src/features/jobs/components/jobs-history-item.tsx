import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'

import type { JobStatusResponse } from '@/shared/api'
import { Badge, type BadgeProps } from '@/shared/ui/badge'

export interface JobsHistoryItemProps {
  readonly job: JobStatusResponse
}

interface StatusPresentation {
  readonly labelKey: string
  readonly variant: NonNullable<BadgeProps['variant']>
}

const STATUS_PRESENTATIONS: Readonly<Record<string, StatusPresentation>> = {
  pending: { labelKey: 'jobs.history.status.preparing', variant: 'neutral' },
  uploaded: { labelKey: 'jobs.history.status.queued', variant: 'neutral' },
  running: { labelKey: 'jobs.history.status.processing', variant: 'processing' },
  completed: { labelKey: 'jobs.history.status.completed', variant: 'success' },
  failed: { labelKey: 'jobs.history.status.failed', variant: 'danger' },
}

/** Render one public job summary with a destination determined by its status. */
export function JobsHistoryItem({ job }: JobsHistoryItemProps) {
  const { i18n, t } = useTranslation()
  const status = getStatusPresentation(job.status)
  const statusLabel = t(status.labelKey)
  const pipelineLabel =
    job.pipeline_type === 'copy_adaptation' ? t('jobs.pipeline.adaptation') : t('jobs.pipeline.analysis')
  const locale = i18n.resolvedLanguage?.startsWith('en') === true ? 'en-US' : 'pt-BR'
  const destination =
    job.status === 'completed' ? `/app/jobs/${job.job_id}/result` : `/app/jobs/${job.job_id}`

  return (
    <li>
      <Link
        aria-label={t('jobs.history.item.ariaLabel', {
          pipeline: pipelineLabel,
          id: job.job_id,
          status: statusLabel,
        })}
        className="group grid gap-4 border-b border-border px-5 py-5 transition-colors last:border-b-0 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-inset focus-visible:ring-focus sm:px-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.55fr)_minmax(12rem,0.8fr)_auto] lg:items-center lg:gap-6"
        to={destination}
      >
        <div className="min-w-0">
          <p className="text-body font-semibold text-text transition-colors group-hover:text-action">
            {pipelineLabel}
          </p>
          <p className="mt-1 font-mono text-meta text-text-subtle">
            {t('jobs.projectNumber', { id: job.job_id })}
          </p>
        </div>

        <div>
          <span className="mb-1.5 block text-meta text-text-subtle lg:hidden">
            {t('jobs.history.list.columns.status')}
          </span>
          <Badge variant={status.variant}>{statusLabel}</Badge>
        </div>

        <div>
          <span className="mb-1 block text-meta text-text-subtle lg:hidden">
            {t('jobs.history.list.columns.created')}
          </span>
          <time className="text-body-sm text-text-muted" dateTime={job.created_at}>
            {formatJobDate(job.created_at, locale, t('jobs.dateUnavailable'))}
          </time>
        </div>

        <span className="inline-flex items-center gap-2 text-label text-action lg:justify-self-end">
          {job.status === 'completed'
            ? t('jobs.history.item.viewResult')
            : t('jobs.history.item.viewStatus')}
          <ArrowIcon />
        </span>
      </Link>
    </li>
  )
}

function getStatusPresentation(status: string): StatusPresentation {
  return STATUS_PRESENTATIONS[status] ?? { labelKey: 'jobs.history.status.unknown', variant: 'neutral' }
}

function formatJobDate(value: string, locale: string, fallback: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return fallback
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 transition-transform group-hover:translate-x-1"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="M3 8h10m-4-4 4 4-4 4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}
