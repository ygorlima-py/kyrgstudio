/** Convert a route parameter into the positive integer required by the API. */
export function parseJobId(value: string | undefined): number | null {
  if (value === undefined || !/^[1-9]\d*$/.test(value)) {
    return null
  }

  const jobId = Number(value)

  return Number.isSafeInteger(jobId) ? jobId : null
}
