const apiBaseUrl = import.meta.env.VITE_API_BASE_URL.trim()
const authCsrfCookieName = import.meta.env.VITE_AUTH_CSRF_COOKIE_NAME.trim()

if (!apiBaseUrl) {
  throw new Error('VITE_API_BASE_URL is required')
}

if (!authCsrfCookieName) {
  throw new Error('VITE_AUTH_CSRF_COOKIE_NAME is required')
}

export const environment = Object.freeze({
  apiBaseUrl,
  authCsrfCookieName,
})
