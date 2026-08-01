const apiBaseUrl = import.meta.env.VITE_API_BASE_URL.trim()
const authCsrfCookieName =
  import.meta.env.VITE_AUTH_CSRF_COOKIE_NAME.trim()

const maxUploadBytes = Number.parseInt(
  import.meta.env.VITE_MAX_UPLOAD_BYTES,
  10,
)

const acceptedMediaTypes = [
  ...new Set(
    import.meta.env.VITE_ACCEPTED_MEDIA_TYPES
      .split(',')
      .map((mediaType) => mediaType.trim().toLowerCase())
      .filter(Boolean),
  ),
]

if (!apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is required')
}

if (!authCsrfCookieName) {
  throw new Error('VITE_AUTH_CSRF_COOKIE_NAME is required')
}

if (
  !Number.isSafeInteger(maxUploadBytes) ||
  maxUploadBytes <= 0
) {
  throw new Error(
    'VITE_MAX_UPLOAD_BYTES must be a positive integer',
  )
}

if (acceptedMediaTypes.length === 0) {
  throw new Error(
    'VITE_ACCEPTED_MEDIA_TYPES must contain at least one media type',
  )
}

export const environment = Object.freeze({
  apiBaseUrl,
  authCsrfCookieName,
  maxUploadBytes,
  acceptedMediaTypes: Object.freeze(acceptedMediaTypes),
})