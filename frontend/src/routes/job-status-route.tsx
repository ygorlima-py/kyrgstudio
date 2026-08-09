import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'

import {
  isKnownJobStatus,
  JobStatusPanel,
  parseJobId,
  useJobStatus,
} from '@/features/jobs'
import {
  ErrorState,
  LoadingState,
  NotFoundState,
} from '@/shared/components/states'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'

const actionLinkClassName =
  'inline-flex h-11 items-center justify-center rounded-md bg-action px-4 text-label text-text-inverse transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2'

/** Recover and display a persisted project directly from the job id in the URL. */
export function JobStatusRoute() {
  const { t } = useTranslation()
  const { jobId: routeJobId } = useParams()
  const jobId = parseJobId(routeJobId)

  if (jobId === null) {
    return (
      <NotFoundState
        action={
          <Link className={actionLinkClassName} to="/app">
            {t('jobStatus.actions.returnToDashboard')}
          </Link>
        }
        description={t('jobStatus.invalid.description')}
        title={t('jobStatus.invalid.title')}
      />
    )
  }

  return <PersistedJobStatus jobId={jobId} />
}

function PersistedJobStatus({ jobId }: { readonly jobId: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const statusQuery = useJobStatus(jobId)
  const jobStatus = statusQuery.data?.status

  useEffect(() => {
    if (jobStatus === 'completed') {
      void navigate(`/app/jobs/${jobId}/result`, { replace: true })
    }
  }, [jobId, jobStatus, navigate])

  if (statusQuery.isPending) {
    return (
      <div className="mx-auto w-full max-w-5xl">
        <LoadingState label={t('jobStatus.loading')} />
      </div>
    )
  }

  if (statusQuery.data === undefined) {
    if (statusQuery.error?.status === 404) {
      return (
        <NotFoundState
          action={
            <Link className={actionLinkClassName} to="/app">
              {t('jobStatus.actions.returnToDashboard')}
            </Link>
          }
          description={t('jobStatus.notFound.description')}
          title={t('jobStatus.notFound.title')}
        />
      )
    }

    return (
      <ErrorState
        action={
          statusQuery.error?.retryable ? (
            <Button onClick={() => void statusQuery.refetch()} type="button">
              {t('jobStatus.actions.retry')}
            </Button>
          ) : (
            <Link className={actionLinkClassName} to="/app">
              {t('jobStatus.actions.returnToDashboard')}
            </Link>
          )
        }
        description={t('jobStatus.unavailable.description')}
        title={t('jobStatus.unavailable.title')}
      />
    )
  }

  if (!isKnownJobStatus(statusQuery.data.status)) {
    return (
      <ErrorState
        action={
          <Button onClick={() => void statusQuery.refetch()} type="button">
            {t('jobStatus.actions.refresh')}
          </Button>
        }
        description={t('jobStatus.unknown.description')}
        title={t('jobStatus.unavailable.title')}
      />
    )
  }

  const job = {
    ...statusQuery.data,
    status: statusQuery.data.status,
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-5">
      <header>
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('jobStatus.page.eyebrow')}
        </p>
      </header>

      {statusQuery.isError ? (
        <Alert heading={t('jobStatus.reconnecting.title')} variant="warning">
          {t('jobStatus.reconnecting.description')}
        </Alert>
      ) : null}

      <JobStatusPanel
        action={
          job.status === 'failed' ? (
            <>
              <Link className={actionLinkClassName} to="/app/jobs/new">
                {t('jobStatus.actions.startAnother')}
              </Link>
              <Link className="inline-flex h-11 items-center px-2 text-label text-text-muted hover:text-text" to="/app">
                {t('jobStatus.actions.returnToDashboard')}
              </Link>
            </>
          ) : undefined
        }
        job={job}
      />
    </div>
  )
}
