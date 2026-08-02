import { Link } from 'react-router'

import { JobsHistoryFilters } from '@/features/jobs/components/jobs-history-filters'
import { JobsHistoryList } from '@/features/jobs/components/jobs-history-list'
import { useJobsHistoryFilters } from '@/features/jobs/hooks/use-jobs-history-filters'
import { useUserJobs } from '@/features/jobs/hooks/use-user-jobs'

/** Authenticated page for revisiting the user's most recent projects. */
export function JobsHistoryRoute() {
  const filters = useJobsHistoryFilters()
  const jobsQuery = useUserJobs({
    jobId: filters.jobId,
    status: filters.status,
    pipelineType: filters.pipelineType,
    limit: filters.limit,
    offset: filters.offset,
  })
  const jobs = jobsQuery.data?.items ?? []

  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="border-b border-border pb-7 sm:flex sm:items-end sm:justify-between sm:gap-8 sm:pb-9">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
            Project library
          </p>
          <h1 className="mt-2 font-heading text-heading-3 text-text">Project history</h1>
          <p className="mt-2 max-w-2xl text-body text-text-muted">
            Reopen finished work and follow projects that are still processing.
          </p>
        </div>

        <Link
          className="mt-5 inline-flex h-10 items-center justify-center rounded-md border border-border-strong bg-surface px-4 text-label text-text shadow-sm transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2 sm:mt-0 sm:shrink-0"
          to="/app/jobs/new"
        >
          New project
        </Link>
      </header>

      <div className="pt-7 sm:pt-9">
        <JobsHistoryFilters
          hasActiveFilters={filters.hasActiveFilters}
          jobId={filters.jobId}
          onClear={filters.clearFilters}
          onJobIdChange={filters.setJobId}
          onPipelineTypeChange={filters.setPipelineType}
          onStatusChange={filters.setStatus}
          pipelineType={filters.pipelineType}
          status={filters.status}
        />

        <div className="pt-7">
          <JobsHistoryList
            currentPage={filters.page}
            hasActiveFilters={filters.hasActiveFilters}
            isError={jobsQuery.isError && jobsQuery.data === undefined}
            hasMore={jobsQuery.data?.has_more ?? false}
            isLoading={jobsQuery.isPending}
            jobs={jobs}
            onClearFilters={filters.clearFilters}
            onNextPage={() => filters.setPage(filters.page + 1)}
            onPreviousPage={() => filters.setPage(Math.max(1, filters.page - 1))}
            onRetry={() => void jobsQuery.refetch()}
          />
        </div>
      </div>
    </div>
  )
}
