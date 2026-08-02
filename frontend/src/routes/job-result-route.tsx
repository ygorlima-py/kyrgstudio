import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router'

import {
  AdaptationResult,
  AdaptationResultValidationError,
  useAdaptationResult,
} from '@/features/copy-adaptation'
import {
  AnalysisResult,
  AnalysisResultValidationError,
  useJobResult,
} from '@/features/copy-analysis'
import { isActiveJobStatus, parseJobId, useJobStatus } from '@/features/jobs'
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

type PipelineType = 'copy_analysis' | 'copy_adaptation'

/** Load the completed result identified by the protected route parameter. */
export function JobResultRoute() {
  const { jobId: routeJobId } = useParams()
  const jobId = parseJobId(routeJobId)

  if (jobId === null) {
    return (
      <NotFoundState
        action={dashboardLink()}
        description="The project address is invalid or no longer available."
        title="Project not found"
      />
    )
  }

  return <PersistedJobResult jobId={jobId} />
}

/** Resolve the pipeline type before mounting its specialized result hook. */
function PersistedJobResult({ jobId }: { readonly jobId: number }) {
  const statusQuery = useJobStatus(jobId)

  if (statusQuery.isPending) {
    return <ResultLoadingState label="Loading project" />
  }

  if (statusQuery.data === undefined) {
    return renderLookupError(statusQuery.error, () => {
      void statusQuery.refetch()
    })
  }

  const job = statusQuery.data

  if (job.status !== 'completed') {
    return renderIncompleteJob(jobId, job.status)
  }

  return job.pipeline_type === 'copy_adaptation' ? (
    <PersistedAdaptationResult jobId={jobId} />
  ) : (
    <PersistedAnalysisResult jobId={jobId} />
  )
}

function PersistedAnalysisResult({ jobId }: { readonly jobId: number }) {
  const resultQuery = useJobResult(jobId)

  if (resultQuery.isPending) {
    return <ResultLoadingState label="Loading copy analysis" />
  }

  if (resultQuery.data === undefined) {
    return renderResultError('copy_analysis', jobId, resultQuery.error, () => {
      void resultQuery.refetch()
    })
  }

  return (
    <ResultPage
      description="A structured reading of the message, offer, persuasion strategy, and improvement opportunities."
      eyebrow="Copy analysis"
      jobId={jobId}
      newJobLabel="Analyze another copy"
      newJobUrl="/app/jobs/new?pipeline=copy_analysis"
      title="Analysis result"
    >
      <AnalysisResult result={resultQuery.data} />
    </ResultPage>
  )
}

function PersistedAdaptationResult({ jobId }: { readonly jobId: number }) {
  const resultQuery = useAdaptationResult(jobId)

  if (resultQuery.isPending) {
    return <ResultLoadingState label="Loading adapted script" />
  }

  if (resultQuery.data === undefined) {
    return renderResultError('copy_adaptation', jobId, resultQuery.error, () => {
      void resultQuery.refetch()
    })
  }

  return (
    <ResultPage
      description="Review the adapted script, refine its wording, and verify its evidence and production-readiness checks."
      eyebrow="Copy adaptation"
      jobId={jobId}
      newJobLabel="Adapt another copy"
      newJobUrl="/app/jobs/new?pipeline=copy_adaptation"
      title="Adapted script"
    >
      <AdaptationResult result={resultQuery.data} />
    </ResultPage>
  )
}

interface ResultPageProps {
  readonly children: ReactNode
  readonly description: string
  readonly eyebrow: string
  readonly jobId: number
  readonly newJobLabel: string
  readonly newJobUrl: string
  readonly title: string
}

function ResultPage({
  children,
  description,
  eyebrow,
  jobId,
  newJobLabel,
  newJobUrl,
  title,
}: ResultPageProps) {
  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="mb-10 border-b border-border pb-7 sm:mb-12 sm:flex sm:items-end sm:justify-between sm:gap-8 sm:pb-9">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">{eyebrow}</p>
          <h1 className="mt-2 font-heading text-heading-2 text-text">{title}</h1>
          <p className="mt-3 max-w-2xl text-body text-text-muted">{description}</p>
        </div>

        <p className="mt-5 shrink-0 font-mono text-meta uppercase tracking-[0.1em] text-text-subtle sm:mt-0 sm:pb-1">
          Project #{jobId}
        </p>
      </header>

      {children}

      <footer className="mt-16 flex flex-wrap gap-3 border-t border-border pt-7 sm:mt-20">
        <Link className={primaryLinkClassName} to={newJobUrl}>
          {newJobLabel}
        </Link>
        <Link className={secondaryLinkClassName} to="/app">
          Return to dashboard
        </Link>
      </footer>
    </div>
  )
}

function ResultLoadingState({ label }: { readonly label: string }) {
  return (
    <div className="mx-auto w-full max-w-6xl">
      <LoadingState label={label} />
    </div>
  )
}

function renderIncompleteJob(jobId: number, status: string) {
  if (isActiveJobStatus(status)) {
    return (
      <ProcessingState
        action={statusLink(jobId)}
        description="This project has not produced a completed result yet. Return to its status page while processing continues."
        progressLabel="Project is still processing"
        statusLabel="Not ready yet"
        title="Your result is still being prepared"
      />
    )
  }

  if (status === 'failed') {
    return (
      <ErrorState
        action={statusLink(jobId)}
        description="This project stopped before producing a result. Open its status page for the public failure information."
        title="Project did not complete"
      />
    )
  }

  return (
    <ErrorState
      action={statusLink(jobId)}
      description="This project does not currently have a result that can be displayed."
      title="Result unavailable"
    />
  )
}

function renderLookupError(error: Error, retry: () => void) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <NotFoundState
        action={dashboardLink()}
        description="This project does not exist or is not available to your account."
        title="Project not found"
      />
    )
  }

  return renderGenericLoadError(error, retry)
}

function renderResultError(
  pipelineType: PipelineType,
  jobId: number,
  error: Error,
  retry: () => void,
) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <NotFoundState
        action={dashboardLink()}
        description="This project does not exist or is not available to your account."
        title="Project not found"
      />
    )
  }

  if (error instanceof ApiError && error.status === 409) {
    return (
      <ProcessingState
        action={statusLink(jobId)}
        description="This project has not produced a completed result yet. Return to its status page while processing continues."
        progressLabel="Project is still processing"
        statusLabel="Not ready yet"
        title="Your result is still being prepared"
      />
    )
  }

  if (
    error instanceof AnalysisResultValidationError ||
    error instanceof AdaptationResultValidationError
  ) {
    const resultLabel = pipelineType === 'copy_adaptation' ? 'adaptation' : 'analysis'

    return (
      <ErrorState
        action={dashboardLink()}
        description={`The completed project returned an ${resultLabel} format this version of the application cannot display safely.`}
        title="Result format is unavailable"
      />
    )
  }

  return renderGenericLoadError(error, retry)
}

function renderGenericLoadError(error: Error, retry: () => void) {
  const canRetry = error instanceof ApiError && error.retryable

  return (
    <ErrorState
      action={
        canRetry ? (
          <Button onClick={retry} type="button">
            Try again
          </Button>
        ) : (
          dashboardLink()
        )
      }
      description="We could not load this result. No internal error details were exposed."
      title="Result unavailable"
    />
  )
}

function dashboardLink() {
  return (
    <Link className={primaryLinkClassName} to="/app">
      Return to dashboard
    </Link>
  )
}

function statusLink(jobId: number) {
  return (
    <Link className={primaryLinkClassName} to={`/app/jobs/${jobId}`}>
      View processing status
    </Link>
  )
}
