import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'

import { ApiError } from '@/shared/api'
import { i18n } from '@/shared/i18n/i18n'
import { LoginRoute } from '@/routes/login-route'
import { RegisterRoute } from '@/routes/register-route'
import { VerifyEmailRoute } from '@/routes/verify-email-route'

const authMocks = vi.hoisted(() => ({
  loginWithPassword: vi.fn(),
  registerWithPassword: vi.fn(),
  resendEmailVerification: vi.fn(),
}))

vi.mock('@/features/auth/hooks/use-auth', () => ({
  useAuth: () => ({
    status: 'anonymous',
    user: null,
    loginWithPassword: authMocks.loginWithPassword,
    logout: vi.fn(),
    registerWithPassword: authMocks.registerWithPassword,
    resendEmailVerification: authMocks.resendEmailVerification,
  }),
}))

describe('email verification flow', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    window.sessionStorage.clear()
    authMocks.loginWithPassword.mockReset()
    authMocks.registerWithPassword.mockReset()
    authMocks.resendEmailVerification.mockReset()
  })

  it('continues from registration to the pending verification screen', async () => {
    const user = userEvent.setup()
    authMocks.registerWithPassword.mockResolvedValue({
      email: 'creator@example.com',
      email_verification_required: true,
    })

    renderFlow('/register')

    await user.type(screen.getByLabelText('Name'), 'Ada Creator')
    await user.type(screen.getByLabelText('Email'), 'creator@example.com')
    await user.type(screen.getByLabelText('Password'), 'secure-pass')
    await user.type(screen.getByLabelText('Confirm your password'), 'secure-pass')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Confirm your email' })).toBeInTheDocument()
    expect(screen.getByText('creator@example.com')).toBeInTheDocument()
    expect(authMocks.registerWithPassword).toHaveBeenCalledWith({
      email: 'creator@example.com',
      name: 'Ada Creator',
      password: 'secure-pass',
    })
  })

  it('redirects an unverified login to the pending verification screen', async () => {
    const user = userEvent.setup()
    authMocks.loginWithPassword.mockRejectedValue(
      new ApiError({
        code: 'email_verification_required',
        details: {},
        retryable: false,
        status: 403,
        step: 'validating_email_verification',
      }),
    )

    renderFlow('/login')

    await user.type(screen.getByLabelText('Email'), 'waiting@example.com')
    await user.type(screen.getByLabelText('Password'), 'secure-pass')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('heading', { name: 'Confirm your email' })).toBeInTheDocument()
    expect(screen.getByText('waiting@example.com')).toBeInTheDocument()
  })

  it('resends the confirmation and starts a cooldown', async () => {
    const user = userEvent.setup()
    authMocks.resendEmailVerification.mockResolvedValue({ sent: true })

    renderFlow({
      pathname: '/verify-email',
      state: { email: 'waiting@example.com' },
    })

    await user.click(screen.getByRole('button', { name: 'Resend confirmation email' }))

    expect(authMocks.resendEmailVerification).toHaveBeenCalledWith({
      email: 'waiting@example.com',
    })
    expect(
      await screen.findByText(
        'A new confirmation email is on its way. Check your inbox and spam folder.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Resend in 60s' })).toBeDisabled()
  })
})

function renderFlow(initialEntry: string | { pathname: string; state: unknown }) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/register" element={<RegisterRoute />} />
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/verify-email" element={<VerifyEmailRoute />} />
        <Route path="/app" element={<h1>Workspace</h1>} />
      </Routes>
    </MemoryRouter>,
  )
}
