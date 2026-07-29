export function LandingRoute() {
  return (
    <main className="min-h-screen bg-background px-6 py-16 text-text">
      <section className="mx-auto max-w-reading rounded-lg border border-border bg-surface p-8 shadow-md">
        <span className="inline-flex rounded-pill bg-processing-muted px-3 py-1 text-sm text-processing">
          Design system
        </span>

        <h1 className="mt-6 text-4xl font-semibold tracking-tight">Kyrg Studio</h1>

        <p className="mt-4 text-lg text-text-muted">
          Creative intelligence for analyzing and adapting direct-response copy.
        </p>

        <button
          className="mt-8 rounded-md bg-action px-5 py-3 font-semibold text-text-inverse transition-colors hover:bg-action-hover"
          type="button"
        >
          Analyze a copy
        </button>
      </section>
    </main>
  )
}
