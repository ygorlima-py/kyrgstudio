import { useTranslation } from 'react-i18next'

import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const workflowSteps = ['upload', 'process', 'result'] as const

/**
 * Explains the product workflow from source upload to structured output.
 */
export function HowItWorks() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="how-it-works-title"
      className="bg-surface-muted py-20 sm:py-24 lg:py-32"
      id="how-it-works"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
              {t('marketing.howItWorks.badge')}
            </span>

            <h2
              className="font-heading text-heading-2 text-text"
              id="how-it-works-title"
            >
              {t('marketing.howItWorks.title')}
            </h2>

            <p className="text-body-lg text-text-muted">
              {t('marketing.howItWorks.description')}
            </p>
          </Stack>

          <ol className="grid gap-4 md:grid-cols-3">
            {workflowSteps.map((step) => (
              <li className="flex" key={step}>
                <Card className="w-full" padding="lg">
                  <Stack gap="lg">
                    <span className="font-mono text-meta text-action">
                      {t('marketing.howItWorks.stepLabel')}{' '}
                      {t(`marketing.howItWorks.steps.${step}.number`)}
                    </span>

                    <Stack gap="sm">
                      <h3 className="font-heading text-heading-3 text-text">
                        {t(`marketing.howItWorks.steps.${step}.title`)}
                      </h3>

                      <p className="text-body text-text-muted">
                        {t(`marketing.howItWorks.steps.${step}.description`)}
                      </p>
                    </Stack>
                  </Stack>
                </Card>
              </li>
            ))}
          </ol>

          <Card padding="lg" variant="elevated">
            <div className="grid gap-8 md:grid-cols-2 md:gap-0">
              <Stack className="md:pr-8" gap="sm">
                <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
                  {t('marketing.howItWorks.outputs.analysis.badge')}
                </span>

                <h3 className="font-heading text-heading-3 text-text">
                  {t('marketing.howItWorks.outputs.analysis.title')}
                </h3>

                <p className="text-body text-text-muted">
                  {t('marketing.howItWorks.outputs.analysis.description')}
                </p>
              </Stack>

              <Stack
                className="border-t border-border pt-8 md:border-t-0 md:border-l md:pt-0 md:pl-8"
                gap="sm"
              >
                <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
                  {t('marketing.howItWorks.outputs.adaptation.badge')}
                </span>

                <h3 className="font-heading text-heading-3 text-text">
                  {t('marketing.howItWorks.outputs.adaptation.title')}
                </h3>

                <p className="text-body text-text-muted">
                  {t('marketing.howItWorks.outputs.adaptation.description')}
                </p>
              </Stack>
            </div>
          </Card>
        </Stack>
      </Container>
    </section>
  )
}