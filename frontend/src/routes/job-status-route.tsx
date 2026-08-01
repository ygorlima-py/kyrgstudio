import { useEffect } from 'react'
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
  const { jobId: routeJobId } = useParams()
  const jobId = parseJobId(routeJobId)

  if (jobId === null) {
    return (
      <NotFoundState
        action={<Link className={actionLinkClassName} to="/app">Return to dashboard</Link>}
        description="The project address is invalid or no longer available."
        title="Project not found"
      />
    )
  }

  return <PersistedJobStatus jobId={jobId} />
}

function PersistedJobStatus({ jobId }: { readonly jobId: number }) {
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
        <LoadingState label="Loading project status" />
      </div>
    )
  }

  if (statusQuery.data === undefined) {
    if (statusQuery.error?.status === 404) {
      return (
        <NotFoundState
          action={<Link className={actionLinkClassName} to="/app">Return to dashboard</Link>}
          description="This project does not exist or is not available to your account."
          title="Project not found"
        />
      )
    }

    return (
      <ErrorState
        action={
          statusQuery.error?.retryable ? (
            <Button onClick={() => void statusQuery.refetch()} type="button">
              Try again
            </Button>
          ) : (
            <Link className={actionLinkClassName} to="/app">
              Return to dashboard
            </Link>
          )
        }
        description="We could not load the latest project status."
        title="Status unavailable"
      />
    )
  }

  if (!isKnownJobStatus(statusQuery.data.status)) {
    return (
      <ErrorState
        action={<Button onClick={() => void statusQuery.refetch()} type="button">Refresh status</Button>}
        description="The project returned a status this version of the application does not recognize."
        title="Status unavailable"
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
          Project status
        </p>
      </header>

      {statusQuery.isError ? (
        <Alert heading="Reconnecting" variant="warning">
          The last known status is shown while we reconnect to the server.
        </Alert>
      ) : null}

      <JobStatusPanel
        action={
          job.status === 'failed' ? (
            <>
              <Link className={actionLinkClassName} to="/app/jobs/new">
                Start another project
              </Link>
              <Link className="inline-flex h-11 items-center px-2 text-label text-text-muted hover:text-text" to="/app">
                Return to dashboard
              </Link>
            </>
          ) : undefined
        }
        job={job}
      />
    </div>
  )
}
