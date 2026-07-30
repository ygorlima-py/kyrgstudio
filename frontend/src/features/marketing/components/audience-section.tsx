import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const audiences = [
  {
    number: '01',
    role: 'Copywriters',
    title: 'Study the strategy, not only the words.',
    description:
      'Turn reference videos into structured material you can inspect and use while developing new scripts.',
    benefits: [
      'Map hooks, mechanisms, proof and CTAs',
      'Identify persuasion patterns and strategic gaps',
      'Adapt the structure to a different offer',
    ],
  },
  {
    number: '02',
    role: 'Marketers',
    title: 'Review the message before investing in distribution.',
    description:
      'Understand how an offer is presented and where the copy needs stronger clarity, proof or positioning.',
    benefits: [
      'Review promises and offer consistency',
      'Find unsupported claims and missing proof',
      'Create clearer briefs for creative teams',
    ],
  },
  {
    number: '03',
    role: 'Producers',
    title: 'Turn spoken content into an organized creative asset.',
    description:
      'Move from a raw video or audio file to structured analysis and an editable script without reading raw JSON.',
    benefits: [
      'Work from a complete transcription',
      'Navigate the content by strategic section',
      'Review an adapted script in an editable format',
    ],
  },
] as const

/**
 * Connects the product capabilities to the practical needs of its primary
 * professional audiences.
 */
export function AudienceSection() {
  return (
    <section
      aria-labelledby="audience-title"
      className="bg-text py-20 text-text-inverse sm:py-24 lg:py-32"
      id="audience"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <Badge variant="action">Who it is for</Badge>

            <h2
              className="font-heading text-heading-2 text-text-inverse"
              id="audience-title"
            >
              A clearer workspace for people responsible for the message.
            </h2>

            <p className="text-body-lg text-border">
              Kyrg Studio helps creative professionals understand, review and
              adapt direct-response content without reducing the work to a
              generic AI conversation.
            </p>
          </Stack>

          <ul className="grid gap-4 lg:grid-cols-3">
            {audiences.map((audience) => (
              <li className="flex" key={audience.number}>
                <Card className="w-full" padding="lg" variant="elevated">
                  <Stack className="h-full" gap="lg">
                    <div className="flex items-center justify-between gap-4">
                      <span className="font-mono text-meta text-action">
                        {audience.number}
                      </span>

                      <Badge variant="neutral">{audience.role}</Badge>
                    </div>

                    <Stack gap="sm">
                      <h3 className="font-heading text-heading-3 text-text">
                        {audience.title}
                      </h3>

                      <p className="text-body text-text-muted">
                        {audience.description}
                      </p>
                    </Stack>

                    <ul className="mt-auto grid gap-3">
                      {audience.benefits.map((benefit) => (
                        <li
                          className="grid grid-cols-[0.5rem_1fr] items-start gap-3 text-body-sm text-text-muted"
                          key={benefit}
                        >
                          <span
                            aria-hidden="true"
                            className="mt-2 size-2 rounded-pill bg-action"
                          />

                          <span>{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </Stack>
                </Card>
              </li>
            ))}
          </ul>
        </Stack>
      </Container>
    </section>
  )
}