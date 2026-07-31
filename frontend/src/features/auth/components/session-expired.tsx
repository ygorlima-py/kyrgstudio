/**
 * Explains why the user was redirected to the login page.
 */
export function SessionExpired() {
  return (
    <div
      className="border-l-2 border-warning pl-4"
      role="status"
    >
      <p className="text-label text-text">Your session expired</p>
      <p className="mt-1 text-body-sm text-text-muted">
        Log in again to continue where you left off.
      </p>
    </div>
  )
}