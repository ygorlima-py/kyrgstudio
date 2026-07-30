import { Link } from 'react-router'

import { Container } from '@/shared/ui/container'
import { Separator } from '@/shared/ui/separator'
import { Stack } from '@/shared/ui/stack'

/**
 * Provides public product navigation and account access at the end of every
 * marketing page.
 */
export function MarketingFooter() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-border bg-background">
      <Container>
        <div className="grid gap-12 py-12 md:grid-cols-[1.4fr_1fr] lg:py-16">
          <Stack className="max-w-md" gap="md">
            <Link
              className="w-fit font-heading text-2xl font-semibold text-text"
              to="/"
            >
              Kyrg Studio
            </Link>

            <p className="text-body text-text-muted">
              Creative intelligence for understanding and adapting
              direct-response copy from video and audio.
            </p>

            <p className="font-mono text-meta uppercase text-text-subtle">
              Analysis · Adaptation · Structured output
            </p>
          </Stack>

          <nav
            aria-label="Footer navigation"
            className="grid grid-cols-2 gap-8"
          >
            <Stack gap="sm">
              <p className="font-mono text-meta uppercase text-text-subtle">
                Product
              </p>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#product-preview"
              >
                Product preview
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#how-it-works"
              >
                How it works
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#features"
              >
                Features
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#faq"
              >
                FAQ
              </a>
            </Stack>

            <Stack gap="sm">
              <p className="font-mono text-meta uppercase text-text-subtle">
                Account
              </p>

              <Link
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                to="/login"
              >
                Log in
              </Link>

              <Link
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                to="/register"
              >
                Create account
              </Link>
            </Stack>
          </nav>
        </div>

        <Separator decorative />

        <div className="flex flex-col gap-3 py-6 text-body-sm text-text-subtle sm:flex-row sm:items-center sm:justify-between">
          <p>© {currentYear} Kyrg Studio.</p>

          <p>Built for deliberate creative work.</p>
        </div>
      </Container>
    </footer>
  )
}