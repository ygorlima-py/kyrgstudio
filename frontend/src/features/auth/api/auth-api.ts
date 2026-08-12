import { environment } from '@/shared/config/environment'
import {
  apiClient,
  type AccessTokenResponse,
  type CurrentUserResponse,
  type ForgotPasswordRequest,
  type PasswordLoginRequest,
  type PasswordResetRequestedResponse,
  type RegisterRequest,
  type RegisterResponse,
  type ResendEmailVerificationRequest,
  type ResendEmailVerificationResponse,
  type ResetPasswordRequest,
} from '@/shared/api'

const CSRF_HEADER_NAME = 'X-CSRF-Token'

/**
 * Creates an account that must be confirmed before authentication.
 */
export async function registerWithPassword(request: RegisterRequest): Promise<RegisterResponse> {
  const response = await apiClient.post<RegisterResponse>('/auth/register', request)

  return response.data
}

/**
 * Requests a fresh confirmation email without revealing account existence.
 */
export async function resendEmailVerification(
  request: ResendEmailVerificationRequest,
): Promise<ResendEmailVerificationResponse> {
  const response = await apiClient.post<ResendEmailVerificationResponse>(
    '/auth/resend-verification-email',
    request,
  )

  return response.data
}

/**
 * Requests a password-reset email without exposing whether the email exists.
 *
 * Errors are normalized by the shared Axios client before they reach the
 * caller, just like the other authentication operations.
 */
export async function requestPasswordReset(
  request: ForgotPasswordRequest,
): Promise<PasswordResetRequestedResponse> {
  const response = await apiClient.post<PasswordResetRequestedResponse>(
    '/auth/forgot-password',
    request,
  )

  return response.data
}

/**
 * Replaces the account password using the opaque token from the email link.
 */
export async function resetPassword(request: ResetPasswordRequest): Promise<void> {
  await apiClient.post<void>('/auth/reset-password', request)
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
