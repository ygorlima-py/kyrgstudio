import axios, { isAxiosError } from 'axios'
import type { AxiosResponse } from 'axios'

import { environment } from '@/shared/config/environment'

import { normalizeApiError } from './errors'
import {
  accessTokenRefreshCoordinator,
  type AccessTokenRefresh,
} from './refresh-coordinator'

let accessToken: string | null = null
let refreshAccessToken: AccessTokenRefresh | null = null

/**
 * Shared Axios client used by all application features.
 */
export const apiClient = axios.create({
  baseURL: environment.apiBaseUrl,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
})

/**
 * Updates the access token attached to subsequent requests.
 */
export function setApiAccessToken(token: string | null): void {
  const normalizedToken = token?.trim() ?? ''
  accessToken = normalizedToken.length > 0 ? normalizedToken : null
}

/**
 * Removes the current access token.
 */
export function clearApiAccessToken(): void {
  accessToken = null
}

/**
 * Registers the authentication operation used to renew an expired token.
 */
export function configureApiTokenRefresh(
  refreshHandler: AccessTokenRefresh | null,
): void {
  refreshAccessToken = refreshHandler
}

apiClient.interceptors.request.use((config) => {
  if (accessToken !== null) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  } else {
    config.headers.delete('Authorization')
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  handleResponseFailure,
)

async function handleResponseFailure(
  error: unknown,
): Promise<AxiosResponse<unknown>> {
  const refreshHandler = refreshAccessToken

  if (
    !isAxiosError(error) ||
    error.response?.status !== 401 ||
    error.config === undefined ||
    accessToken === null ||
    refreshHandler === null ||
    isRefreshRequest(error.config.url)
  ) {
    throw normalizeApiError(error)
  }

  let refreshedToken: string

  try {
    refreshedToken =
      await accessTokenRefreshCoordinator.refresh(refreshHandler)
  } catch (refreshError) {
    clearApiAccessToken()
    throw normalizeApiError(refreshError)
  }

  setApiAccessToken(refreshedToken)
  error.config.headers.set(
    'Authorization',
    `Bearer ${refreshedToken}`,
  )

  try {
    // Static Axios avoids sending the retried request through this interceptor
    // again, preventing an infinite refresh loop.
    return await axios.request(error.config)
  } catch (retryError) {
    throw normalizeApiError(retryError)
  }
}

function isRefreshRequest(url: string | undefined): boolean {
  return url?.includes('/auth/refresh') ?? false
}