import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'

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
  const { t } = useTranslation()

  if (isLoading) {
    return <JobsHistoryLoading />
  }

  if (isError) {
    return (
      <ErrorState
        action={
          <Button onClick={onRetry} size="sm" variant="secondary">
            {t('jobs.history.error.retry')}
          </Button>
        }
        description={t('jobs.history.error.description')}
        title={t('jobs.history.error.title')}
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
        {t('jobs.history.list.title')}
      </h2>

      <div
        aria-hidden="true"
        className="hidden grid-cols-[minmax(0,1.35fr)_minmax(8rem,0.55fr)_minmax(12rem,0.8fr)_auto] gap-6 rounded-t-lg border-x border-t border-border bg-surface-muted px-6 py-3 text-meta uppercase tracking-[0.08em] text-text-subtle lg:grid"
      >
        <span>{t('jobs.history.list.columns.project')}</span>
        <span>{t('jobs.history.list.columns.status')}</span>
        <span>{t('jobs.history.list.columns.created')}</span>
        <span className="text-right">{t('jobs.history.list.columns.open')}</span>
      </div>

      <ul className="overflow-hidden rounded-lg border border-border bg-surface lg:rounded-t-none">
        {jobs.map((job) => (
          <JobsHistoryItem job={job} key={job.job_id} />
        ))}
      </ul>

      {currentPage > 1 || hasMore ? (
        <nav
          aria-label={t('jobs.history.pagination.ariaLabel')}
          className="mt-5 flex items-center justify-between gap-4"
        >
          <Button
            disabled={currentPage === 1}
            onClick={onPreviousPage}
            size="sm"
            type="button"
            variant="secondary"
          >
            {t('jobs.history.pagination.previous')}
          </Button>

          <span aria-live="polite" className="font-mono text-meta text-text-muted">
            {t('jobs.history.pagination.page', { page: currentPage })}
          </span>

          <Button
            disabled={!hasMore}
            onClick={onNextPage}
            size="sm"
            type="button"
            variant="secondary"
          >
            {t('jobs.history.pagination.next')}
          </Button>
        </nav>
      ) : null}
    </section>
  )
}

function JobsHistoryLoading() {
  const { t } = useTranslation()

  return (
    <LoadingState label={t('jobs.history.loading.label')}>
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
  const { t } = useTranslation()

  return (
    <EmptyState
      action={
        <Link
          className="inline-flex h-10 items-center justify-center rounded-md bg-action px-4 text-label text-text-inverse transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2"
          to="/app/jobs/new"
        >
          {t('jobs.history.empty.action')}
        </Link>
      }
      description={t('jobs.history.empty.description')}
      title={t('jobs.history.empty.title')}
    />
  )
}

function NoSearchResults({ onClear }: { readonly onClear: () => void }) {
  const { t } = useTranslation()

  return (
    <EmptyState
      action={
        <Button onClick={onClear} size="sm" variant="secondary">
          {t('jobs.history.filters.clear')}
        </Button>
      }
      description={t('jobs.history.noResults.description')}
      title={t('jobs.history.noResults.title')}
    />
  )
}
