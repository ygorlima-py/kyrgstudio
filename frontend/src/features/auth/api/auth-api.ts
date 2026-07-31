import { environment } from '@/shared/config/environment'
import {
  apiClient,
  type AccessTokenResponse,
  type CurrentUserResponse,
  type PasswordLoginRequest,
  type RegisterRequest,
} from '@/shared/api'

const CSRF_HEADER_NAME = 'X-CSRF-Token'

/**
 * Creates an account authenticated with email and password.
 */
export async function registerWithPassword(request: RegisterRequest): Promise<AccessTokenResponse> {
  const response = await apiClient.post<AccessTokenResponse>('/auth/register', request)

  return response.data
}

/**
 * Authenticates an existing account with email and password.
 */
export async function loginWithPassword(
  request: PasswordLoginRequest,
): Promise<AccessTokenResponse> {
  const response = await apiClient.post<AccessTokenResponse>('/auth/login', request)

  return response.data
}

/**
 * Rotates the protected refresh session and returns a new access token.
 */
export async function refreshAuthentication(): Promise<AccessTokenResponse> {
  const response = await apiClient.post<AccessTokenResponse>('/auth/refresh', undefined, {
    headers: csrfHeaders(),
  })

  return response.data
}

/**
 * Revokes the current refresh session on the backend.
 */
export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout', undefined, {
    headers: csrfHeaders(),
  })
}

/**
 * Returns the identity represented by the current access token.
 */
export async function getCurrentUser(): Promise<CurrentUserResponse> {
  const response = await apiClient.get<CurrentUserResponse>('/auth/me')
  return response.data
}

function csrfHeaders(): Record<string, string> {
  const csrfToken = readCookie(environment.authCsrfCookieName)

  if (csrfToken === null) {
    return {}
  }

  return {
    [CSRF_HEADER_NAME]: csrfToken,
  }
}

function readCookie(cookieName: string): string | null {
  if (typeof document === 'undefined') {
    return null
  }

  const expectedPrefix = `${cookieName}=`
  const cookie = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(expectedPrefix))

  if (cookie === undefined) {
    return null
  }

  const encodedValue = cookie.slice(expectedPrefix.length)

  try {
    return decodeURIComponent(encodedValue)
  } catch {
    return null
  }
}
