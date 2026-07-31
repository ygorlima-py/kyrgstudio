import { Link, Outlet } from 'react-router'

/**
 * Shared page structure for authentication routes.
 */
export function AuthLayout() {
  return (
    <div className="min-h-svh bg-background text-text">
      <header className="flex h-20 items-center justify-between px-6 lg:px-10">
        <Link
          className="font-heading text-2xl font-semibold tracking-tight"
          to="/"
        >
          Kyrg Studio
        </Link>

        <Link
          className="text-label text-text-muted transition-colors hover:text-text"
          to="/"
        >
          Back to home
        </Link>
      </header>

      <main className="grid min-h-[calc(100svh-5rem)] lg:grid-cols-[minmax(0,1fr)_minmax(28rem,0.72fr)]">
        <section className="hidden border-r border-border bg-surface-muted px-10 py-16 lg:flex lg:flex-col lg:justify-end">
          <p className="mb-5 font-mono text-meta uppercase tracking-[0.16em] text-action">
            Analyze. Understand. Adapt.
          </p>

          <h1 className="max-w-2xl font-heading text-display-sm text-text">
            Turn proven sales messages into strategy you can actually use.
          </h1>

          <p className="mt-6 max-w-xl text-body-lg text-text-muted">
            Upload a sales video, uncover how its message works, and adapt the
            structure to your own offer.
          </p>
        </section>

        <section className="flex items-center justify-center px-6 py-12 sm:px-10">
          <div className="w-full max-w-md">
            <Outlet />
          </div>
        </section>
      </main>
    </div>
  )
}