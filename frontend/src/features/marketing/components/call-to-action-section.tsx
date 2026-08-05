import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Container } from '@/shared/ui/container'
import { Inline } from '@/shared/ui/inline'
import { Stack } from '@/shared/ui/stack'

/**
 * Closes the marketing page with a clear conversion path for new and returning
 * users.
 */
export function CallToActionSection() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="final-cta-title"
      className="py-20 sm:py-24 lg:py-32"
    >
      <Container>
        <div
          className={[
            'relative overflow-hidden rounded-xl bg-action',
            'px-6 py-12 text-text-inverse',
            'sm:px-10 sm:py-16 lg:px-16 lg:py-20',
          ].join(' ')}
        >
          <div
            aria-hidden="true"
            className={[
              'absolute -top-24 -right-24 size-80 rounded-pill',
              'border-[3rem] border-action-hover opacity-50',
            ].join(' ')}
          />

          <div className="relative grid items-end gap-12 lg:grid-cols-[1fr_auto]">
            <Stack className="max-w-3xl" gap="md">
              <p className="font-mono text-meta uppercase text-text-inverse">
                {t('marketing.callToAction.eyebrow')}
              </p>

              <h2
                className="font-heading text-heading-2 text-text-inverse"
                id="final-cta-title"
              >
                {t('marketing.callToAction.title')}
              </h2>

              <p className="max-w-2xl text-body-lg text-text-inverse">
                {t('marketing.callToAction.description')}
              </p>
            </Stack>

            <Inline align="center" gap="sm">
              <Link
                className={[
                  'inline-flex min-h-12 items-center justify-center rounded-md',
                  'bg-surface px-6 text-label font-semibold text-action shadow-sm',
                  'transition-colors duration-(--duration-fast) ease-standard',
                  'hover:bg-surface-muted',
                  'focus-visible:outline-none focus-visible:ring-3',
                  'focus-visible:ring-focus focus-visible:ring-offset-2',
                  'focus-visible:ring-offset-action',
                ].join(' ')}
                to="/register"
              >
                {t('marketing.callToAction.createAccount')}
              </Link>
            </Inline>
          </div>
        </div>
      </Container>
    </section>
  )
}