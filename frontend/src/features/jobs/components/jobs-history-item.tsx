import { Link } from 'react-router'

import type { JobStatusResponse } from '@/shared/api'
import { Badge, type BadgeProps } from '@/shared/ui/badge'

export interface JobsHistoryItemProps {
  readonly job: JobStatusResponse
}

interface StatusPresentation {
  readonly label: string
  readonly variant: NonNullable<BadgeProps['variant']>
}

const STATUS_PRESENTATIONS: Readonly<Record<string, StatusPresentation>> = {
  pending: { label: 'Preparing', variant: 'neutral' },
  uploaded: { label: 'Queued', variant: 'neutral' },
  running: { label: 'Processing', variant: 'processing' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
}

/** Render one public job summary with a destination determined by its status. */
export function JobsHistoryItem({ job }: JobsHistoryItemProps) {
  const status = getStatusPresentation(job.status)
  const destination =
    job.status === 'completed' ? `/app/jobs/${job.job_id}/result` : `/app/jobs/${job.job_id}`

  return (
    <li>
      <Link
        aria-label={`${getPipelineLabel(job.pipeline_type)}, project ${job.job_id}, ${status.label}`}
        className="group grid gap-4 border-b border-border px-5 py-5 transition-colors last:border-b-0 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-inset focus-visible:ring-focus sm:px-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.55fr)_minmax(12rem,0.8fr)_auto] lg:items-center lg:gap-6"
        to={destination}
      >
        <div className="min-w-0">
          <p className="text-body font-semibold text-text transition-colors group-hover:text-action">
            {getPipelineLabel(job.pipeline_type)}
          </p>
          <p className="mt-1 font-mono text-meta text-text-subtle">Project #{job.job_id}</p>
        </div>

        <div>
          <span className="mb-1.5 block text-meta text-text-subtle lg:hidden">Status</span>
          <Badge variant={status.variant}>{status.label}</Badge>
        </div>

        <div>
          <span className="mb-1 block text-meta text-text-subtle lg:hidden">Created</span>
          <time className="text-body-sm text-text-muted" dateTime={job.created_at}>
            {formatJobDate(job.created_at)}
          </time>
        </div>

        <span className="inline-flex items-center gap-2 text-label text-action lg:justify-self-end">
          {job.status === 'completed' ? 'View result' : 'View status'}
          <ArrowIcon />
        </span>
      </Link>
    </li>
  )
}

function getPipelineLabel(pipelineType: JobStatusResponse['pipeline_type']): string {
  return pipelineType === 'copy_adaptation' ? 'Copy adaptation' : 'Copy analysis'
}

function getStatusPresentation(status: string): StatusPresentation {
  return STATUS_PRESENTATIONS[status] ?? { label: 'Unknown', variant: 'neutral' }
}

function formatJobDate(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
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
