import { useContext } from 'react'

import { AuthContext } from '../context/auth-context'
import type { AuthContextValue } from '../types/auth-types'

/** Returns the current authentication state and available authentication actions. */
export function useAuth(): AuthContextValue {
  const auth = useContext(AuthContext)

  if (auth === null) {
    throw new Error('useAuth must be used inside AuthProvider.')
  }

  return auth
}