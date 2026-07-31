import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import {
  clearApiAccessToken,
  configureApiTokenRefresh,
  setApiAccessToken,
  type AccessTokenResponse,
  type PasswordLoginRequest,
  type RegisterRequest,
  type CurrentUserResponse,
} from '@/shared/api'

import {
  getCurrentUser,
  loginWithPassword as requestPasswordLogin,
  logout as requestLogout,
  refreshAuthentication,
  registerWithPassword as requestPasswordRegistration,
} from '../api/auth-api'
import type { AuthContextValue, AuthSession } from '../types/auth-types'
import { AuthContext } from './auth-context'

const INITIAL_SESSION: AuthSession = {
  status: 'anonymous',
  user: null,
}

const RESTORING_SESSION: AuthSession = {
  status: 'restoring',
  user: null,
}

let activeSessionRestoration:
  Promise<CurrentUserResponse> | null = null

type AuthProviderProps = PropsWithChildren

/**
 * Owns the authenticated user and coordinates access-token state in memory.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<AuthSession>(RESTORING_SESSION)

  const establishAuthenticatedSession = useCallback(
    async (authentication: AccessTokenResponse): Promise<void> => {
      setApiAccessToken(authentication.access_token)

      try {
        const currentUser = await getCurrentUser()

        setSession({
          status: 'authenticated',
          user: currentUser,
        })
      } catch (error) {
        clearApiAccessToken()
        setSession(INITIAL_SESSION)
        throw error
      }
    },
    [],
  )

  const registerWithPassword = useCallback(
    async (request: RegisterRequest): Promise<void> => {
      const authentication = await requestPasswordRegistration(request)

      await establishAuthenticatedSession(authentication)
    },
    [establishAuthenticatedSession],
  )

  const loginWithPassword = useCallback(
    async (request: PasswordLoginRequest): Promise<void> => {
      const authentication = await requestPasswordLogin(request)

      await establishAuthenticatedSession(authentication)
    },
    [establishAuthenticatedSession],
  )

  const logout = useCallback(async (): Promise<void> => {
    try {
      await requestLogout()
    } finally {
      clearApiAccessToken()
      setSession(INITIAL_SESSION)
    }
  }, [])

  const refreshAccessToken = useCallback(async (): Promise<string> => {
    try {
      const authentication = await refreshAuthentication()
      return authentication.access_token
    } catch (error) {
      clearApiAccessToken()

      setSession((currentSession) => {
        if (currentSession.status !== 'authenticated') {
          return currentSession
        }

        return {
          status: 'expired',
          user: null,
        }
      })

      throw error
    }
  }, [])

  useEffect(() => {
    configureApiTokenRefresh(refreshAccessToken)

    return () => {
      configureApiTokenRefresh(null)
      clearApiAccessToken()
    }
  }, [refreshAccessToken])

  useEffect(() => {
    let isSubscribed = true

    void restorePersistedSession()
      .then((currentUser) => {
        if (!isSubscribed) {
          return
        }

        setSession({
          status: 'authenticated',
          user: currentUser,
        })
      })
      .catch(() => {
        if (!isSubscribed) {
          return
        }

        setSession(INITIAL_SESSION)
      })

    return () => {
      isSubscribed = false
    }
  }, [])

  const contextValue = useMemo<AuthContextValue>(
    () => ({
      ...session,
      registerWithPassword,
      loginWithPassword,
      logout,
    }),
    [session, registerWithPassword, loginWithPassword, logout],
  )

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

function restorePersistedSession(): Promise<CurrentUserResponse> {
  if (activeSessionRestoration !== null) {
    return activeSessionRestoration
  }

  activeSessionRestoration = executeSessionRestoration()
  return activeSessionRestoration
}

async function executeSessionRestoration(): Promise<CurrentUserResponse> {
  try {
    const authentication = await refreshAuthentication()

    setApiAccessToken(authentication.access_token)

    return await getCurrentUser()
  } catch (error) {
    clearApiAccessToken()
    throw error
  } finally {
    activeSessionRestoration = null
  }
}
