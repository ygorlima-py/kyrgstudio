import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'

import { ApiError } from '@/shared/api'
import { resetPassword } from '@/features/auth/api/auth-api'
import { i18n } from '@/shared/i18n/i18n'
import { ResetPasswordRoute } from '@/routes/reset-password-route'

vi.mock('@/features/auth/api/auth-api', () => ({
  resetPassword: vi.fn(),
}))

const resetPasswordMock = vi.mocked(resetPassword)

describe('password reset flow', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    resetPasswordMock.mockReset()
  })

  it('sends the fragment token only when the new passwords are valid', async () => {
    const user = userEvent.setup()
    resetPasswordMock.mockResolvedValue(undefined)

    renderResetPassword('/reset-password#token=one-time-token')

    await user.type(screen.getByLabelText('New password'), 'new-secure-password')
    await user.type(screen.getByLabelText('Confirm your new password'), 'new-secure-password')
    await user.click(screen.getByRole('button', { name: 'Save new password' }))

    expect(resetPasswordMock).toHaveBeenCalledWith({
      token: 'one-time-token',
      new_password: 'new-secure-password',
    })
    expect(await screen.findByText('Password updated')).toBeInTheDocument()
  })

  it('does not submit when the passwords do not match', async () => {
    const user = userEvent.setup()

    renderResetPassword('/reset-password#token=one-time-token')

    await user.type(screen.getByLabelText('New password'), 'new-secure-password')
    await user.type(screen.getByLabelText('Confirm your new password'), 'different-password')
    await user.click(screen.getByRole('button', { name: 'Save new password' }))

    expect(resetPasswordMock).not.toHaveBeenCalled()
    expect(await screen.findByText('Passwords do not match.')).toBeInTheDocument()
  })

  it('offers a new link when the backend rejects the reset token', async () => {
    const user = userEvent.setup()
    resetPasswordMock.mockRejectedValue(
      new ApiError({
        code: 'invalid_input',
        details: { field: 'token' },
        retryable: false,
        status: 422,
        step: 'validating_reset_token',
      }),
    )

    renderResetPassword('/reset-password#token=expired-token')

    await user.type(screen.getByLabelText('New password'), 'new-secure-password')
    await user.type(screen.getByLabelText('Confirm your new password'), 'new-secure-password')
    await user.click(screen.getByRole('button', { name: 'Save new password' }))

    expect(
      await screen.findByText(
        'This recovery link is invalid or has expired. Request a new link and try again.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Request a new link' })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
  })
})

function renderResetPassword(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordRoute />} />
      </Routes>
    </MemoryRouter>,
  )
}
