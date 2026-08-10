import type {
  CurrentUserResponse,
  PasswordLoginRequest,
  RegisterRequest,
  RegisterResponse,
  ResendEmailVerificationRequest,
  ResendEmailVerificationResponse,
} from '@/shared/api'

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
  readonly registerWithPassword: (request: RegisterRequest) => Promise<RegisterResponse>

  readonly resendEmailVerification: (
    request: ResendEmailVerificationRequest,
  ) => Promise<ResendEmailVerificationResponse>

  readonly loginWithPassword: (request: PasswordLoginRequest) => Promise<void>

  readonly logout: () => Promise<void>
}

/**
 * Public authentication state exposed by AuthProvider.
 */
export type AuthContextValue = AuthSession & AuthActions
