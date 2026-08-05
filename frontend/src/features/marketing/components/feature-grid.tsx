import { useTranslation } from 'react-i18next'

import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

const features = [
  {
    id: 'structure',
    layout: 'md:col-span-2',
    accent: 'border-2 border-action bg-transparent text-action',
  },
  {
    id: 'offer',
    layout: 'md:col-span-1',
    accent: 'border-2 border-action bg-transparent text-action',
  },
  {
    id: 'gaps',
    layout: 'md:col-span-1',
    accent: 'border-2 border-action bg-transparent text-action',
  },
  {
    id: 'adaptation',
    layout: 'md:col-span-2',
    accent: 'border-2 border-action bg-transparent text-action',
  },
  {
    id: 'integrity',
    layout: 'md:col-span-2',
    accent: 'border-2 border-action bg-transparent text-action',
  },
  {
    id: 'output',
    layout: 'md:col-span-1',
    accent: 'border-2 border-action bg-transparent text-action',
  },
] as const

/**
 * Presents the primary product capabilities as concrete creative benefits.
 */
export function FeatureGrid() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="features-title"
      className="py-20 sm:py-24 lg:py-32"
      id="features"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
              {t('marketing.features.badge')}
            </span>

            <h2
              className="font-heading text-heading-2 text-text"
              id="features-title"
            >
              {t('marketing.features.title')}
            </h2>

            <p className="text-body-lg text-text-muted">
              {t('marketing.features.description')}
            </p>
          </Stack>

          <ul className="grid gap-4 md:grid-cols-3">
            {features.map((feature) => {
              const translationPath = `marketing.features.items.${feature.id}`

              return (
                <li className={feature.layout} key={feature.id}>
                  <Card
                    className={[
                      'group h-full',
                      'transition-transform duration-(--duration-normal)',
                      'ease-standard motion-safe:hover:-translate-y-1',
                    ].join(' ')}
                    padding="lg"
                  >
                    <Stack className="h-full" gap="lg">
                      <div
                        className={cn(
                          'flex size-11 items-center justify-center',
                          'rounded-md font-mono text-meta font-semibold',
                          feature.accent,
                        )}
                      >
                        {t(`${translationPath}.number`)}
                      </div>

                      <Stack gap="sm">
                        <span className="text-label text-text-muted">
                          {t(`${translationPath}.category`)}
                        </span>

                        <h3 className="font-heading text-heading-3 text-text">
                          {t(`${translationPath}.title`)}
                        </h3>

                        <p className="text-body text-text-muted">
                          {t(`${translationPath}.description`)}
                        </p>
                      </Stack>
                    </Stack>
                  </Card>
                </li>
              )
            })}
          </ul>
        </Stack>
      </Container>
    </section>
  )
}