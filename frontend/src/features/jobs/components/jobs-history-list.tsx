import { Link } from 'react-router'

import type { JobStatusResponse } from '@/shared/api'
import { EmptyState, ErrorState, LoadingState } from '@/shared/components/states'
import { Button } from '@/shared/ui/button'
import { Skeleton } from '@/shared/ui/skeleton'

import { JobsHistoryItem } from './jobs-history-item'

export interface JobsHistoryListProps {
  readonly currentPage: number
  readonly hasMore: boolean
  readonly jobs: readonly JobStatusResponse[]
  readonly isError: boolean
  readonly hasActiveFilters: boolean
  readonly isLoading: boolean
  readonly onClearFilters: () => void
  readonly onNextPage: () => void
  readonly onPreviousPage: () => void
  readonly onRetry: () => void
}

/** Present a job page and the complete set of loading, error, and empty states. */
export function JobsHistoryList({
  currentPage,
  hasActiveFilters,
  hasMore,
  isError,
  isLoading,
  jobs,
  onClearFilters,
  onNextPage,
  onPreviousPage,
  onRetry,
}: JobsHistoryListProps) {
  if (isLoading) {
    return <JobsHistoryLoading />
  }

  if (isError) {
    return (
      <ErrorState
        action={
          <Button onClick={onRetry} size="sm" variant="secondary">
            Try again
          </Button>
        }
        description="We could not load your project history. Your saved work was not affected."
        title="Project history is temporarily unavailable"
      />
    )
  }

  if (jobs.length === 0) {
    return hasActiveFilters || currentPage > 1 ? (
      <NoSearchResults onClear={onClearFilters} />
    ) : (
      <EmptyHistory />
    )
  }

  return (
    <section aria-labelledby="jobs-history-list-heading">
      <h2 className="sr-only" id="jobs-history-list-heading">
        Your projects
      </h2>

      <div
        aria-hidden="true"
        className="hidden grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.55fr)_minmax(12rem,0.8fr)_auto] gap-6 rounded-t-lg border-x border-t border-border bg-surface-muted px-6 py-3 text-meta uppercase tracking-[0.08em] text-text-subtle lg:grid"
      >
        <span>Project</span>
        <span>Status</span>
        <span>Created</span>
        <span className="text-right">Open</span>
      </div>

      <ul className="overflow-hidden rounded-lg border border-border bg-surface lg:rounded-t-none">
        {jobs.map((job) => (
          <JobsHistoryItem job={job} key={job.job_id} />
        ))}
      </ul>

      {currentPage > 1 || hasMore ? (
        <nav
          aria-label="Project history pages"
          className="mt-5 flex items-center justify-between gap-4"
        >
          <Button
            disabled={currentPage === 1}
            onClick={onPreviousPage}
            size="sm"
            type="button"
            variant="secondary"
          >
            Previous
          </Button>

          <span aria-live="polite" className="font-mono text-meta text-text-muted">
            Page {currentPage}
          </span>

          <Button
            disabled={!hasMore}
            onClick={onNextPage}
            size="sm"
            type="button"
            variant="secondary"
          >
            Next
          </Button>
        </nav>
      ) : null}
    </section>
  )
}

function JobsHistoryLoading() {
  return (
    <LoadingState label="Loading project history">
      <div
        aria-hidden="true"
        className="overflow-hidden rounded-lg border border-border bg-surface"
      >
        {[0, 1, 2, 3].map((item) => (
          <div
            className="grid gap-4 border-b border-border px-5 py-5 last:border-b-0 sm:px-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.55fr)_minmax(12rem,0.8fr)_auto] lg:items-center lg:gap-6"
            key={item}
          >
            <div>
              <Skeleton className="h-5 w-40" />
              <Skeleton className="mt-2 h-3 w-24" />
            </div>
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-4 w-20 lg:justify-self-end" />
          </div>
        ))}
      </div>
    </LoadingState>
  )
}

function EmptyHistory() {
  return (
    <EmptyState
      action={
        <Link
          className="inline-flex h-10 items-center justify-center rounded-md bg-action px-4 text-label text-text-inverse transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2"
          to="/app/jobs/new"
        >
          Start a project
        </Link>
      }
      description="Your analyses and adaptations will be kept here so you can return to them later."
      title="No projects yet"
    />
  )
}

function NoSearchResults({ onClear }: { readonly onClear: () => void }) {
  return (
    <EmptyState
      action={
        <Button onClick={onClear} size="sm" variant="secondary">
          Clear filters
        </Button>
      }
      description="Try changing or clearing the current search and filters."
      title="No matching projects"
    />
  )
}
