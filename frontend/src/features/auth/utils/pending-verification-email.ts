const PENDING_EMAIL_STORAGE_KEY = 'kyrg_pending_verification_email'

/** Resolve a pending verification email from navigation state or session storage. */
export function resolvePendingVerificationEmail(locationState: unknown): string | null {
  const stateEmail = readEmailFromLocationState(locationState)

  if (stateEmail !== null) {
    return stateEmail
  }

  if (typeof window === 'undefined') {
    return null
  }

  try {
    return normalizeEmail(window.sessionStorage.getItem(PENDING_EMAIL_STORAGE_KEY))
  } catch {
    return null
  }
}

/** Persist the pending email only for the current browser session. */
export function storePendingVerificationEmail(email: string): void {
  if (typeof window === 'undefined') {
    return
  }

  const normalizedEmail = normalizeEmail(email)

  if (normalizedEmail === null) {
    return
  }

  try {
    window.sessionStorage.setItem(PENDING_EMAIL_STORAGE_KEY, normalizedEmail)
  } catch {
    // Verification remains usable through navigation state in restricted browsers.
  }
}

/** Remove stale registration data after authentication or an email change. */
export function clearPendingVerificationEmail(): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    window.sessionStorage.removeItem(PENDING_EMAIL_STORAGE_KEY)
  } catch {
    // Authentication must not fail because browser storage is unavailable.
  }
}

function readEmailFromLocationState(locationState: unknown): string | null {
  if (typeof locationState !== 'object' || locationState === null || !('email' in locationState)) {
    return null
  }

  return normalizeEmail(locationState.email)
}

function normalizeEmail(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }

  const normalizedEmail = value.trim().toLowerCase()

  if (
    normalizedEmail.length < 3 ||
    normalizedEmail.length > 320 ||
    !normalizedEmail.includes('@')
  ) {
    return null
  }

  return normalizedEmail
}
