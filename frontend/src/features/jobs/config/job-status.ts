/** Job states currently persisted and exposed by the public API. */
export const JOB_STATUSES = [
  'uploaded',
  'running',
  'completed',
  'failed',
] as const

export type JobStatus = (typeof JOB_STATUSES)[number]

/** Return whether the API value belongs to the status contract understood by the UI. */
export function isKnownJobStatus(status: string): status is JobStatus {
  return JOB_STATUSES.some((knownStatus) => knownStatus === status)
}

/** Active jobs continue to be refreshed until they reach a terminal state. */
export function isActiveJobStatus(status: string | undefined): boolean {
  return status === 'uploaded' || status === 'running'
}

/** Terminal jobs no longer need status polling. */
export function isTerminalJobStatus(status: string | undefined): boolean {
  return status === 'completed' || status === 'failed'
}
