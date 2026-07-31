import type { CurrentUserResponse, PasswordLoginRequest, RegisterRequest } from '@/shared/api'

export type AuthSession =
  | {
      readonly status: 'restoring'
      readonly user: null
    }
  | {
      readonly status: 'anonymous'
      readonly user: null
    }
  | {
      readonly status: 'authenticated'
      readonly user: CurrentUserResponse
    }
  | {
      readonly status: 'expired'
      readonly user: null
    }

/**
 * Authentication operations available to application components.
 */
export interface AuthActions {
  readonly registerWithPassword: (request: RegisterRequest) => Promise<void>

  readonly loginWithPassword: (request: PasswordLoginRequest) => Promise<void>

  readonly logout: () => Promise<void>
}

/**
 * Public authentication state exposed by AuthProvider.
 */
export type AuthContextValue = AuthSession & AuthActions
