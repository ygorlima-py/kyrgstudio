import { Link, useParams } from 'react-router'

import {
  AnalysisResult,
  AnalysisResultValidationError,
  useJobResult,
} from '@/features/copy-analysis'
import { parseJobId } from '@/features/jobs'
import { ApiError } from '@/shared/api'
import {
  ErrorState,
  LoadingState,
  NotFoundState,
  ProcessingState,
} from '@/shared/components/states'
import { Button } from '@/shared/ui/button'

const primaryLinkClassName =
  'inline-flex h-11 items-center justify-center rounded-md bg-action px-4 text-label text-text-inverse transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2'

const secondaryLinkClassName =
  'inline-flex h-11 items-center justify-center rounded-md border border-border-strong bg-surface px-4 text-label text-text transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2'

/** Load a completed copy analysis identified by the protected route parameter. */
export function JobResultRoute() {
  const { jobId: routeJobId } = useParams()
  const jobId = parseJobId(routeJobId)

  if (jobId === null) {
    return (
      <NotFoundState
        action={
          <Link className={primaryLinkClassName} to="/app">
            Return to dashboard
          </Link>
        }
        description="The project address is invalid or no longer available."
        title="Analysis not found"
      />
    )
  }

  return <PersistedAnalysisResult jobId={jobId} />
}

function PersistedAnalysisResult({ jobId }: { readonly jobId: number }) {
  const resultQuery = useJobResult(jobId)

  if (resultQuery.isPending) {
    return (
      <div className="mx-auto w-full max-w-6xl">
        <LoadingState label="Loading copy analysis" />
      </div>
    )
  }

  if (resultQuery.data === undefined) {
    return renderResultError(jobId, resultQuery.error, () => {
      void resultQuery.refetch()
    })
  }

  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="mb-10 border-b border-border pb-7 sm:mb-12 sm:flex sm:items-end sm:justify-between sm:gap-8 sm:pb-9">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
            Copy analysis
          </p>

          <h1 className="mt-2 font-heading text-heading-2 text-text">Analysis result</h1>

          <p className="mt-3 max-w-2xl text-body text-text-muted">
            A structured reading of the message, offer, persuasion strategy, and improvement
            opportunities.
          </p>
        </div>

        <p className="mt-5 shrink-0 font-mono text-meta uppercase tracking-[0.1em] text-text-subtle sm:mt-0 sm:pb-1">
          Project #{jobId}
        </p>
      </header>

      <AnalysisResult result={resultQuery.data} />

      <footer className="mt-16 flex flex-wrap gap-3 border-t border-border pt-7 sm:mt-20">
        <Link className={primaryLinkClassName} to="/app/jobs/new?pipeline=copy_analysis">
          Analyze another copy
        </Link>
        <Link className={secondaryLinkClassName} to="/app">
          Return to dashboard
        </Link>
      </footer>
    </div>
  )
}

function renderResultError(jobId: number, error: Error, retry: () => void) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <NotFoundState
        action={
          <Link className={primaryLinkClassName} to="/app">
            Return to dashboard
          </Link>
        }
        description="This project does not exist or is not available to your account."
        title="Analysis not found"
      />
    )
  }

  if (error instanceof ApiError && error.status === 409) {
    return (
      <ProcessingState
        action={
          <Link className={primaryLinkClassName} to={`/app/jobs/${jobId}`}>
            View processing status
          </Link>
        }
        description="This project has not produced a completed result yet. Return to its status page while processing continues."
        progressLabel="Analysis is still processing"
        statusLabel="Not ready yet"
        title="Your analysis is still being prepared"
      />
    )
  }

  if (error instanceof AnalysisResultValidationError) {
    return (
      <ErrorState
        action={
          <Link className={primaryLinkClassName} to="/app">
            Return to dashboard
          </Link>
        }
        description="The completed project returned a result this version of the application cannot display safely."
        title="Analysis format is unavailable"
      />
    )
  }

  const canRetry = error instanceof ApiError && error.retryable

  return (
    <ErrorState
      action={
        canRetry ? (
          <Button onClick={retry} type="button">
            Try again
          </Button>
        ) : (
          <Link className={primaryLinkClassName} to="/app">
            Return to dashboard
          </Link>
        )
      }
      description="We could not load this analysis. No internal error details were exposed."
      title="Analysis unavailable"
    />
  )
}
