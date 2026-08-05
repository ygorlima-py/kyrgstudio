import { useTranslation } from 'react-i18next'

import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const audiences = [
  {
    id: 'copywriters',
    number: '01',
    benefits: ['strategy', 'gaps', 'adaptation'],
  },
  {
    id: 'marketers',
    number: '02',
    benefits: ['promises', 'proof', 'briefs'],
  },
  {
    id: 'producers',
    number: '03',
    benefits: ['transcription', 'navigation', 'editing'],
  },
] as const

/**
 * Connects the product capabilities to the practical needs of its primary
 * professional audiences.
 */
export function AudienceSection() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="audience-title"
      className="bg-text py-20 text-text-inverse sm:py-24 lg:py-32"
      id="audience"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
              {t('marketing.whoItIsFor.badge')}
            </span>

            <h2
              className="font-heading text-heading-2 text-text-inverse"
              id="audience-title"
            >
              {t('marketing.whoItIsFor.title')}
            </h2>

            <p className="text-body-lg text-border">
              {t('marketing.whoItIsFor.description')}
            </p>
          </Stack>

          <ul className="grid gap-4 lg:grid-cols-3">
            {audiences.map((audience) => {
              const translationPath =
                `marketing.whoItIsFor.audiences.${audience.id}`

              return (
                <li className="flex" key={audience.id}>
                  <Card
                    className="w-full"
                    padding="lg"
                    variant="elevated"
                  >
                    <Stack className="h-full" gap="lg">
                      <div className="flex items-center justify-between gap-4">
                        <span className="font-mono text-meta text-action">
                          {audience.number}
                        </span>

                        <Badge variant="neutral">
                          {t(`${translationPath}.role`)}
                        </Badge>
                      </div>

                      <Stack gap="sm">
                        <h3 className="font-heading text-heading-3 text-text">
                          {t(`${translationPath}.title`)}
                        </h3>

                        <p className="text-body text-text-muted">
                          {t(`${translationPath}.description`)}
                        </p>
                      </Stack>

                      <ul className="mt-auto grid gap-3">
                        {audience.benefits.map((benefit) => (
                          <li
                            className={[
                              'grid grid-cols-[0.5rem_1fr] items-start gap-3',
                              'text-body-sm text-text-muted',
                            ].join(' ')}
                            key={benefit}
                          >
                            <span
                              aria-hidden="true"
                              className="mt-2 size-2 rounded-pill bg-action"
                            />

                            <span>
                              {t(`${translationPath}.benefits.${benefit}`)}
                            </span>
                          </li>
                        ))}
                      </ul>
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
