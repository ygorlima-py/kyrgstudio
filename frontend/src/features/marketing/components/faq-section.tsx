import { useTranslation } from 'react-i18next'

import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const frequentlyAskedQuestions = [
  'analysisAndAdaptation',
  'supportedFiles',
  'processing',
  'closeBrowser',
  'uploadedFile',
  'offerProfile',
  'inventedInformation',
] as const

/**
 * Answers common product, processing, and data-handling questions using native
 * disclosure elements that remain accessible without JavaScript state.
 */
export function FaqSection() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="faq-title"
      className="py-20 sm:py-24 lg:py-32"
      id="faq"
    >
      <Container>
        <div className="grid gap-12 lg:grid-cols-[0.75fr_1.25fr] lg:gap-20">
          <Stack className="max-w-xl" gap="md">
            <span className="font-mono text-meta uppercase text-action">
              {t('marketing.faq.badge')}
            </span>

            <h2
              className="font-heading text-heading-2 text-text"
              id="faq-title"
            >
              {t('marketing.faq.title')}
            </h2>

            <p className="text-body-lg text-text-muted">
              {t('marketing.faq.description')}
            </p>
          </Stack>

          <div>
            {frequentlyAskedQuestions.map((questionId) => {
              const translationPath = `marketing.faq.items.${questionId}`

              return (
                <details
                  className="group border-b border-border first:border-t"
                  key={questionId}
                >
                  <summary
                    className={[
                      'flex min-h-20 cursor-pointer list-none items-center',
                      'justify-between gap-6 py-5 text-left',
                      '[&::-webkit-details-marker]:hidden',
                    ].join(' ')}
                  >
                    <span className="text-body font-semibold text-text">
                      {t(`${translationPath}.question`)}
                    </span>

                    <span
                      aria-hidden="true"
                      className="relative size-5 shrink-0 text-text-muted"
                    >
                      <span
                        className={[
                          'absolute top-1/2 left-0 h-px w-full',
                          '-translate-y-1/2 bg-current',
                        ].join(' ')}
                      />

                      <span
                        className={[
                          'absolute top-0 left-1/2 h-full w-px',
                          '-translate-x-1/2 bg-current',
                          'transition-transform duration-(--duration-fast)',
                          'group-open:rotate-90',
                        ].join(' ')}
                      />
                    </span>
                  </summary>

                  <p className="max-w-2xl pb-6 pr-10 text-body text-text-muted">
                    {t(`${translationPath}.answer`)}
                  </p>
                </details>
              )
            })}
          </div>
        </div>
      </Container>
    </section>
  )
}
