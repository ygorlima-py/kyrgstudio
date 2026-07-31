import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

const features = [
  {
    number: '01',
    category: 'Structure',
    title: 'See the architecture behind the words.',
    description:
      'Understand how the hook, problem, promise, mechanism, proof, offer and CTA work together.',
    layout: 'md:col-span-2',
    accent: 'bg-processing-muted text-processing',
  },
  {
    number: '02',
    category: 'Offer',
    title: 'Extract what is actually being sold.',
    description:
      'Identify the audience, pain, desire, promise, benefits, objections and commercial conditions.',
    layout: 'md:col-span-1',
    accent: 'bg-action-muted text-action',
  },
  {
    number: '03',
    category: 'Gaps',
    title: 'Find what weakens the message.',
    description:
      'Surface missing proof, unsupported claims, unclear mechanisms and persuasion gaps.',
    layout: 'md:col-span-1',
    accent: 'bg-warning-muted text-warning',
  },
  {
    number: '04',
    category: 'Adaptation',
    title: 'Reuse strategy without copying the original offer.',
    description:
      'Apply the reference structure to another product while respecting the new audience, promise and restrictions.',
    layout: 'md:col-span-2',
    accent: 'bg-success-muted text-success',
  },
  {
    number: '05',
    category: 'Integrity',
    title: 'Keep claims and proof under control.',
    description:
      'Prevent invented testimonials, guarantees, urgency and commercial details from entering the adapted script.',
    layout: 'md:col-span-2',
    accent: 'bg-danger-muted text-danger',
  },
  {
    number: '06',
    category: 'Output',
    title: 'Work with structured results, not raw AI chat.',
    description:
      'Review organized sections, validation findings, token usage and an editable final script.',
    layout: 'md:col-span-1',
    accent: 'bg-surface-muted text-text-muted',
  },
] as const

/**
 * Presents the primary product capabilities as concrete creative benefits.
 */
export function FeatureGrid() {
  return (
    <section aria-labelledby="features-title" className="py-20 sm:py-24 lg:py-32" id="features">
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <Badge variant="action">Built for real creative work</Badge>

            <h2 className="font-heading text-heading-2 text-text" id="features-title">
              Move from content to decisions, without losing the strategy.
            </h2>

            <p className="text-body-lg text-text-muted">
              Kyrg Studio turns an existing sales message into a structured workspace you can
              inspect, question and adapt.
            </p>
          </Stack>

          <ul className="grid gap-4 md:grid-cols-3">
            {features.map((feature) => (
              <li className={feature.layout} key={feature.number}>
                <Card
                  className="group h-full transition-transform duration-(--duration-normal) ease-standard motion-safe:hover:-translate-y-1"
                  padding="lg"
                >
                  <Stack className="h-full" gap="lg">
                    <div
                      className={cn(
                        'flex size-11 items-center justify-center rounded-md font-mono text-meta',
                        feature.accent,
                      )}
                    >
                      {feature.number}
                    </div>

                    <Stack gap="sm">
                      <span className="text-label text-text-muted">{feature.category}</span>

                      <h3 className="font-heading text-heading-3 text-text">{feature.title}</h3>

                      <p className="text-body text-text-muted">{feature.description}</p>
                    </Stack>
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
