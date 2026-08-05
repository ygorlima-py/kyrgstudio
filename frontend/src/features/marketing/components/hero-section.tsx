import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Container } from '@/shared/ui/container'
import { Inline } from '@/shared/ui/inline'
import { Stack } from '@/shared/ui/stack'

/**
 * Introduces the product value proposition and directs visitors toward the
 * primary conversion or product explanation.
 */
export function HeroSection() {
  const { t } = useTranslation()

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
        
            <Stack gap="md">
              <h1 className="max-w-4xl font-heading text-heading-1 text-text" id="hero-title">
                {t("marketing.hero.title")}
              </h1>

              <p className="max-w-2xl text-body-lg text-text-muted">
                {t("marketing.hero.description")} 
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
                {t("marketing.hero.primaryAction")} 
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
                {t("marketing.hero.secondaryAction")} 
              </a>
            </Inline>

            <p className="font-mono text-meta text-text-subtle"> 
                {t('marketing.hero.meta.analysis')} ·{' '}
                {t('marketing.hero.meta.adaptation')} ·{' '}
                {t('marketing.hero.meta.structuredOutput')}
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
    <div className="relative mx-auto w-full max-w-2xl">
      <div className="absolute -inset-6 rotate-2 rounded-xl border border-border bg-surface-muted" />

      <div className="relative overflow-hidden rounded-xl border border-border bg-surface shadow-xl">
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          className="aspect-video w-full object-cover"
        >
          <source src="/videos/video_hero.mp4" type="video/mp4" />
        </video>
      </div>
    </div>
  )
}

