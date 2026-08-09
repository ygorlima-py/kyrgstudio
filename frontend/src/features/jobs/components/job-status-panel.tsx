import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'

import type { JobStatusResponse } from '@/shared/api'
import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'

import type { JobStatus } from '../config/job-status'
import { JobStatusTimeline } from './job-status-timeline'

type StatusBadgeVariant = 'neutral' | 'processing' | 'success' | 'danger'

interface StatusContent {
  readonly badgeKey: string
  readonly badgeVariant: StatusBadgeVariant
  readonly titleKey: string
  readonly descriptionKey: string
}

const STATUS_CONTENT: Record<JobStatus, StatusContent> = {
  uploaded: {
    badgeKey: 'jobStatus.panel.status.uploaded.badge',
    badgeVariant: 'neutral',
    titleKey: 'jobStatus.panel.status.uploaded.title',
    descriptionKey: 'jobStatus.panel.status.uploaded.description',
  },
  running: {
    badgeKey: 'jobStatus.panel.status.running.badge',
    badgeVariant: 'processing',
    titleKey: 'jobStatus.panel.status.running.title',
    descriptionKey: 'jobStatus.panel.status.running.description',
  },
  completed: {
    badgeKey: 'jobStatus.panel.status.completed.badge',
    badgeVariant: 'success',
    titleKey: 'jobStatus.panel.status.completed.title',
    descriptionKey: 'jobStatus.panel.status.completed.description',
  },
  failed: {
    badgeKey: 'jobStatus.panel.status.failed.badge',
    badgeVariant: 'danger',
    titleKey: 'jobStatus.panel.status.failed.title',
    descriptionKey: 'jobStatus.panel.status.failed.description',
  },
}

export interface JobStatusPanelProps {
  readonly job: JobStatusResponse & { readonly status: JobStatus }
  readonly action?: ReactNode
}

/** Present one persisted job state with a clear, responsive progress line. */
export function JobStatusPanel({ action, job }: JobStatusPanelProps) {
  const { i18n, t } = useTranslation()
  const content = STATUS_CONTENT[job.status]
  const locale = i18n.resolvedLanguage?.startsWith('en') ? 'en-US' : 'pt-BR'

  return (
    <Card className="overflow-hidden" padding="none">
      <div className="border-b border-border px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-3">
            <Badge variant={content.badgeVariant}>
              {t(content.badgeKey)}
            </Badge>

            <div>
              <h1 className="font-heading text-heading-3 text-text">
                {t(content.titleKey)}
              </h1>

              <p className="mt-2 max-w-2xl text-body text-text-muted">
                {job.status === 'failed'
                  ? getPublicFailureDescription(job.error?.code, t)
                  : t(content.descriptionKey)}
              </p>
            </div>
          </div>

          <p className="shrink-0 font-mono text-meta uppercase tracking-[0.12em] text-text-subtle">
            {t('jobStatus.panel.projectNumber', { id: job.job_id })}
          </p>
        </div>
      </div>

      <div className="px-5 py-7 sm:px-8 sm:py-9">
        <JobStatusTimeline status={job.status} />
      </div>

      <div className="border-t border-border px-5 py-5 sm:px-8">
        <dl className="grid gap-4 sm:grid-cols-3">
          <StatusDetail
            label={t('jobStatus.panel.details.projectType')}
            value={
              job.pipeline_type === 'copy_adaptation'
                ? t('jobStatus.panel.pipeline.adaptation')
                : t('jobStatus.panel.pipeline.analysis')
            }
          />
          <StatusDetail
            label={t('jobStatus.panel.details.created')}
            value={formatDateTime(job.created_at, locale, t)}
          />
          <StatusDetail
            label={t('jobStatus.panel.details.elapsedTime')}
            value={formatExecutionTime(job.execution_time_seconds, t)}
          />
        </dl>

        {action ? <div className="mt-6 flex flex-wrap gap-3 border-t border-border pt-5">{action}</div> : null}
      </div>
    </Card>
  )
}

function StatusDetail({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <div>
      <dt className="font-mono text-meta uppercase tracking-[0.1em] text-text-subtle">
        {label}
      </dt>
      <dd className="mt-1 text-body-sm text-text">{value}</dd>
    </div>
  )
}

function formatDateTime(value: string, locale: string, translate: TFunction): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return translate('jobStatus.panel.empty.notAvailable')
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatExecutionTime(value: number | null | undefined, translate: TFunction): string {
  if (value === null || value === undefined) {
    return translate('jobStatus.panel.empty.inProgress')
  }

  if (value < 60) {
    return translate('jobStatus.panel.elapsed.seconds', {
      count: Math.max(0, Math.round(value)),
    })
  }

  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)

  return translate('jobStatus.panel.elapsed.minutesSeconds', {
    minutes,
    seconds,
  })
}

function getPublicFailureDescription(errorCode: string | undefined, translate: TFunction): string {
  switch (errorCode) {
    case 'media_processing_failed':
      return translate('jobStatus.panel.failures.mediaProcessingFailed')
    case 'transcription_failed':
      return translate('jobStatus.panel.failures.transcriptionFailed')
    case 'llm_execution_failed':
    case 'structured_output_failed':
      return translate('jobStatus.panel.failures.structuredOutputFailed')
    case 'storage_error':
      return translate('jobStatus.panel.failures.storageError')
    case 'timeout':
      return translate('jobStatus.panel.failures.timeout')
    default:
      return translate(STATUS_CONTENT.failed.descriptionKey)
  }
}
