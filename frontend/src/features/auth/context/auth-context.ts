import { createContext } from 'react'

import type { AuthContextValue } from '../types/auth-types'

/**
 * Shares the current authentication session with components below AuthProvider.
 */
export const AuthContext = createContext<AuthContextValue | null>(null)
