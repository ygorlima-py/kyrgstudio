import type { ReactNode } from 'react'
import type { TFunction } from 'i18next'
import { Link, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'

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
  const { t } = useTranslation()
  const { jobId: routeJobId } = useParams()
  const jobId = parseJobId(routeJobId)

  if (jobId === null) {
    return (
      <NotFoundState
        action={dashboardLink(t)}
        description={t('jobResult.errors.invalidAddress.description')}
        title={t('jobResult.errors.projectNotFound.title')}
      />
    )
  }

  return <PersistedJobResult jobId={jobId} />
}

/** Resolve the pipeline type before mounting its specialized result hook. */
function PersistedJobResult({ jobId }: { readonly jobId: number }) {
  const { t } = useTranslation()
  const statusQuery = useJobStatus(jobId)

  if (statusQuery.isPending) {
    return <ResultLoadingState label={t('jobResult.loading.project')} />
  }

  if (statusQuery.data === undefined) {
    return renderLookupError(t, statusQuery.error, () => {
      void statusQuery.refetch()
    })
  }

  const job = statusQuery.data

  if (job.status !== 'completed') {
    return renderIncompleteJob(t, jobId, job.status)
  }

  return job.pipeline_type === 'copy_adaptation' ? (
    <PersistedAdaptationResult jobId={jobId} />
  ) : (
    <PersistedAnalysisResult jobId={jobId} />
  )
}

function PersistedAnalysisResult({ jobId }: { readonly jobId: number }) {
  const { t } = useTranslation()
  const resultQuery = useJobResult(jobId)

  if (resultQuery.isPending) {
    return <ResultLoadingState label={t('jobResult.loading.analysis')} />
  }

  if (resultQuery.data === undefined) {
    return renderResultError(t, 'copy_analysis', jobId, resultQuery.error, () => {
      void resultQuery.refetch()
    })
  }

  return (
    <ResultPage
      description={t('analysisResult.page.description')}
      eyebrow={t('analysisResult.page.eyebrow')}
      jobId={jobId}
      newJobLabel={t('analysisResult.page.newJob')}
      newJobUrl="/app/jobs/new?pipeline=copy_analysis"
      title={t('analysisResult.page.title')}
    >
      <AnalysisResult result={resultQuery.data} />
    </ResultPage>
  )
}

function PersistedAdaptationResult({ jobId }: { readonly jobId: number }) {
  const { t } = useTranslation()
  const resultQuery = useAdaptationResult(jobId)

  if (resultQuery.isPending) {
    return <ResultLoadingState label={t('jobResult.loading.adaptation')} />
  }

  if (resultQuery.data === undefined) {
    return renderResultError(t, 'copy_adaptation', jobId, resultQuery.error, () => {
      void resultQuery.refetch()
    })
  }

  return (
    <ResultPage
      description={t('jobResult.adaptation.description')}
      eyebrow={t('jobResult.adaptation.eyebrow')}
      jobId={jobId}
      newJobLabel={t('jobResult.adaptation.newJob')}
      newJobUrl="/app/jobs/new?pipeline=copy_adaptation"
      title={t('jobResult.adaptation.title')}
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
  const { t } = useTranslation()

  return (
    <div className="mx-auto w-full max-w-6xl">
      <header className="mb-10 border-b border-border pb-7 sm:mb-12 sm:flex sm:items-end sm:justify-between sm:gap-8 sm:pb-9">
        <div>
          <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">{eyebrow}</p>
          <h1 className="mt-2 font-heading text-heading-2 text-text">{title}</h1>
          <p className="mt-3 max-w-2xl text-body text-text-muted">{description}</p>
        </div>

        <p className="mt-5 shrink-0 font-mono text-meta uppercase tracking-[0.1em] text-text-subtle sm:mt-0 sm:pb-1">
          {t('jobs.projectNumber', { id: jobId })}
        </p>
      </header>

      {children}

      <footer className="mt-16 flex flex-wrap gap-3 border-t border-border pt-7 sm:mt-20">
        <Link className={primaryLinkClassName} to={newJobUrl}>
          {newJobLabel}
        </Link>
        <Link className={secondaryLinkClassName} to="/app">
          {t('jobResult.actions.returnToDashboard')}
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

function renderIncompleteJob(t: TFunction, jobId: number, status: string) {
  if (isActiveJobStatus(status)) {
    return (
      <ProcessingState
        action={statusLink(t, jobId)}
        description={t('jobResult.errors.notReady.description')}
        progressLabel={t('jobResult.errors.notReady.progressLabel')}
        statusLabel={t('jobResult.errors.notReady.statusLabel')}
        title={t('jobResult.errors.notReady.title')}
      />
    )
  }

  if (status === 'failed') {
    return (
      <ErrorState
        action={statusLink(t, jobId)}
        description={t('jobResult.errors.failed.description')}
        title={t('jobResult.errors.failed.title')}
      />
    )
  }

  return (
    <ErrorState
      action={statusLink(t, jobId)}
      description={t('jobResult.errors.unavailable.description')}
      title={t('jobResult.errors.unavailable.title')}
    />
  )
}

function renderLookupError(t: TFunction, error: Error, retry: () => void) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <NotFoundState
        action={dashboardLink(t)}
        description={t('jobResult.errors.projectNotFound.description')}
        title={t('jobResult.errors.projectNotFound.title')}
      />
    )
  }

  return renderGenericLoadError(t, error, retry)
}

function renderResultError(
  t: TFunction,
  pipelineType: PipelineType,
  jobId: number,
  error: Error,
  retry: () => void,
) {
  if (error instanceof ApiError && error.status === 404) {
    return (
      <NotFoundState
        action={dashboardLink(t)}
        description={t('jobResult.errors.projectNotFound.description')}
        title={t('jobResult.errors.projectNotFound.title')}
      />
    )
  }

  if (error instanceof ApiError && error.status === 409) {
    return (
      <ProcessingState
        action={statusLink(t, jobId)}
        description={t('jobResult.errors.notReady.description')}
        progressLabel={t('jobResult.errors.notReady.progressLabel')}
        statusLabel={t('jobResult.errors.notReady.statusLabel')}
        title={t('jobResult.errors.notReady.title')}
      />
    )
  }

  if (
    error instanceof AnalysisResultValidationError ||
    error instanceof AdaptationResultValidationError
  ) {
    const resultLabel =
      pipelineType === 'copy_adaptation'
        ? t('jobResult.resultTypes.adaptation')
        : t('jobResult.resultTypes.analysis')

    return (
      <ErrorState
        action={dashboardLink(t)}
        description={t('jobResult.errors.invalidFormat.description', { resultType: resultLabel })}
        title={t('jobResult.errors.invalidFormat.title')}
      />
    )
  }

  return renderGenericLoadError(t, error, retry)
}

function renderGenericLoadError(t: TFunction, error: Error, retry: () => void) {
  const canRetry = error instanceof ApiError && error.retryable

  return (
    <ErrorState
      action={
        canRetry ? (
          <Button onClick={retry} type="button">
            {t('jobResult.actions.tryAgain')}
          </Button>
        ) : (
          dashboardLink(t)
        )
      }
      description={t('jobResult.errors.load.description')}
      title={t('jobResult.errors.unavailable.title')}
    />
  )
}

function dashboardLink(t: TFunction) {
  return (
    <Link className={primaryLinkClassName} to="/app">
      {t('jobResult.actions.returnToDashboard')}
    </Link>
  )
}

function statusLink(t: TFunction, jobId: number) {
  return (
    <Link className={primaryLinkClassName} to={`/app/jobs/${jobId}`}>
      {t('jobResult.actions.viewStatus')}
    </Link>
  )
}
