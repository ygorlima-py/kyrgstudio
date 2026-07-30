import { Link } from 'react-router'

import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Inline } from '@/shared/ui/inline'
import { Stack } from '@/shared/ui/stack'

const copySections = [
  {
    label: 'Hook',
    width: 'w-full',
  },
  {
    label: 'Problem',
    width: 'w-4/5',
  },
  {
    label: 'Mechanism',
    width: 'w-3/5',
  },
  {
    label: 'Proof',
    width: 'w-2/3',
  },
  {
    label: 'CTA',
    width: 'w-1/2',
  },
] as const

/**
 * Introduces the product value proposition and directs visitors toward the
 * primary conversion or product explanation.
 */
export function HeroSection() {
  return (
    <section
      aria-labelledby="hero-title"
      className="relative overflow-hidden py-20 sm:py-24 lg:py-32"
    >
      <div
        aria-hidden="true"
        className="absolute top-0 right-0 -z-0 size-96 translate-x-1/3 -translate-y-1/3 rounded-pill bg-action-muted opacity-70 blur-3xl"
      />

      <Container className="relative z-10">
        <div className="grid items-center gap-16 lg:grid-cols-[1.08fr_0.92fr]">
          <Stack align="start" gap="lg">
            <Badge variant="action">
              Creative intelligence for direct response
            </Badge>

            <Stack gap="md">
              <h1
                className="max-w-4xl font-heading text-heading-1 text-text"
                id="hero-title"
              >
                See the strategy inside any sales video. Then make it yours.
              </h1>

              <p className="max-w-2xl text-body-lg text-text-muted">
                Upload a video or audio file. Kyrg Studio identifies its copy
                structure, offer, persuasion strategy and gaps, then helps you
                adapt the strategy to your own offer.
              </p>
            </Stack>

            <Inline gap="sm">
              <Link
                className={[
                  'inline-flex min-h-12 items-center justify-center rounded-md',
                  'bg-action px-6 text-label text-text-inverse shadow-sm',
                  'transition-colors duration-(--duration-fast) ease-standard',
                  'hover:bg-action-hover active:bg-action-active',
                  'focus-visible:outline-none focus-visible:ring-3',
                  'focus-visible:ring-focus focus-visible:ring-offset-2',
                  'focus-visible:ring-offset-background',
                ].join(' ')}
                to="/register"
              >
                Analyze a copy
              </Link>

              <a
                className={[
                  'inline-flex min-h-12 items-center justify-center rounded-md',
                  'border border-border-strong bg-surface px-6 text-label text-text',
                  'transition-colors duration-(--duration-fast) ease-standard',
                  'hover:bg-surface-muted',
                  'focus-visible:outline-none focus-visible:ring-3',
                  'focus-visible:ring-focus focus-visible:ring-offset-2',
                  'focus-visible:ring-offset-background',
                ].join(' ')}
                href="#how-it-works"
              >
                See how it works
              </a>
            </Inline>

            <p className="font-mono text-meta text-text-subtle">
              ANALYSIS · ADAPTATION · STRUCTURED OUTPUT
            </p>
          </Stack>

          <HeroProductIllustration />
        </div>
      </Container>
    </section>
  )
}

/**
 * Decorative product preview that communicates the structured analysis without
 * presenting fabricated customer data or business results.
 */
function HeroProductIllustration() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-xl">
      <div className="absolute -inset-6 rotate-2 rounded-xl border border-border bg-surface-muted" />

      <Card
        className="relative overflow-hidden"
        padding="lg"
        variant="elevated"
      >
        <Stack gap="lg">
          <Inline justify="between">
            <Badge variant="processing">Reference analysis</Badge>

            <span className="font-mono text-meta text-text-subtle">
              COPY MAP
            </span>
          </Inline>

          <Stack gap="sm">
            <span className="text-label text-text-muted">
              Persuasion structure
            </span>

            {copySections.map((section, index) => (
              <div
                className="grid grid-cols-[2rem_1fr] items-center gap-3"
                key={section.label}
              >
                <span className="font-mono text-meta text-text-subtle">
                  {String(index + 1).padStart(2, '0')}
                </span>

                <div
                  className={[
                    'rounded-sm border border-border bg-surface-muted px-3 py-2',
                    section.width,
                  ].join(' ')}
                >
                  <span className="text-label text-text">
                    {section.label}
                  </span>
                </div>
              </div>
            ))}
          </Stack>

          <div className="rounded-md bg-processing-muted p-4">
            <p className="text-label text-processing">Strategic insight</p>
            <p className="mt-1 text-body-sm text-text-muted">
              Structure, offer and persuasion mapped into an editable result.
            </p>
          </div>
        </Stack>
      </Card>
    </div>
  )
}