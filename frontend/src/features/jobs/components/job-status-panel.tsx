import type { ReactNode } from 'react'

import type { JobStatusResponse } from '@/shared/api'
import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'

import type { JobStatus } from '../config/job-status'
import { JobStatusTimeline } from './job-status-timeline'

type StatusBadgeVariant = 'neutral' | 'processing' | 'success' | 'danger'

interface StatusContent {
  readonly badge: string
  readonly badgeVariant: StatusBadgeVariant
  readonly title: string
  readonly description: string
}

const STATUS_CONTENT: Record<JobStatus, StatusContent> = {
  uploaded: {
    badge: 'Waiting to start',
    badgeVariant: 'neutral',
    title: 'Your project is in line',
    description:
      'The file was received successfully. Processing will begin as soon as a worker is available.',
  },
  running: {
    badge: 'Processing',
    badgeVariant: 'processing',
    title: 'We are analyzing your reference',
    description:
      'The transcription and copy analysis are running in the background. You can close this page and return later.',
  },
  completed: {
    badge: 'Completed',
    badgeVariant: 'success',
    title: 'Your result is ready',
    description:
      'Processing finished successfully. We are opening the result now.',
  },
  failed: {
    badge: 'Processing stopped',
    badgeVariant: 'danger',
    title: 'We could not complete this project',
    description:
      'The project stopped before a result was produced. Your account and other projects were not affected.',
  },
}

export interface JobStatusPanelProps {
  readonly job: JobStatusResponse & { readonly status: JobStatus }
  readonly action?: ReactNode
}

/** Present one persisted job state with a clear, responsive progress line. */
export function JobStatusPanel({ action, job }: JobStatusPanelProps) {
  const content = STATUS_CONTENT[job.status]

  return (
    <Card className="overflow-hidden" padding="none">
      <div className="border-b border-border px-5 py-6 sm:px-8 sm:py-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-3">
            <Badge variant={content.badgeVariant}>{content.badge}</Badge>

            <div>
              <h1 className="font-heading text-heading-3 text-text">
                {content.title}
              </h1>

              <p className="mt-2 max-w-2xl text-body text-text-muted">
                {job.status === 'failed'
                  ? getPublicFailureDescription(job.error?.code)
                  : content.description}
              </p>
            </div>
          </div>

          <p className="shrink-0 font-mono text-meta uppercase tracking-[0.12em] text-text-subtle">
            Project #{job.job_id}
          </p>
        </div>
      </div>

      <div className="px-5 py-7 sm:px-8 sm:py-9">
        <JobStatusTimeline status={job.status} />
      </div>

      <div className="border-t border-border px-5 py-5 sm:px-8">
        <dl className="grid gap-4 sm:grid-cols-3">
          <StatusDetail
            label="Project type"
            value={job.pipeline_type === 'copy_adaptation' ? 'Copy adaptation' : 'Copy analysis'}
          />
          <StatusDetail label="Created" value={formatDateTime(job.created_at)} />
          <StatusDetail
            label="Elapsed time"
            value={formatExecutionTime(job.execution_time_seconds)}
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

function formatDateTime(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Not available'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatExecutionTime(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'In progress'
  }

  if (value < 60) {
    return `${Math.max(0, Math.round(value))} seconds`
  }

  const minutes = Math.floor(value / 60)
  const seconds = Math.round(value % 60)

  return `${minutes}m ${seconds}s`
}

function getPublicFailureDescription(errorCode: string | undefined): string {
  switch (errorCode) {
    case 'media_processing_failed':
      return 'The uploaded media could not be read or prepared for analysis.'
    case 'transcription_failed':
      return 'We could not produce a usable transcription from this reference.'
    case 'llm_execution_failed':
    case 'structured_output_failed':
      return 'The analysis service could not produce a valid result for this project.'
    case 'storage_error':
      return 'The reference file became unavailable while the project was processing.'
    case 'timeout':
      return 'Processing took longer than the allowed time and was stopped.'
    default:
      return STATUS_CONTENT.failed.description
  }
}
