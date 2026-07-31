import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const workflowSteps = [
  {
    number: '01',
    title: 'Upload the reference',
    description:
      'Add the video or audio containing the sales message you want to understand or adapt.',
  },
  {
    number: '02',
    title: 'Reveal the strategy',
    description:
      'Kyrg Studio transcribes the content and maps its structure, offer, mechanism, proof and persuasion.',
  },
  {
    number: '03',
    title: 'Choose the output',
    description:
      'Review the complete analysis or provide your offer profile to generate an adapted and validated script.',
  },
] as const

/**
 * Explains the product workflow from source upload to structured output.
 */
export function HowItWorks() {
  return (
    <section
      aria-labelledby="how-it-works-title"
      className="bg-surface-muted py-20 sm:py-24 lg:py-32"
      id="how-it-works"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <Badge variant="action">How it works</Badge>

            <h2 className="font-heading text-heading-2 text-text" id="how-it-works-title">
              One reference. Two ways to turn it into useful creative work.
            </h2>

            <p className="text-body-lg text-text-muted">
              Start with an existing sales video or audio file. Kyrg Studio handles the
              transcription, extracts the strategy and prepares the result for analysis or
              adaptation.
            </p>
          </Stack>

          <ol className="grid gap-4 md:grid-cols-3">
            {workflowSteps.map((step) => (
              <li className="flex" key={step.number}>
                <Card className="w-full" padding="lg">
                  <Stack gap="lg">
                    <span className="font-mono text-meta text-action">STEP {step.number}</span>

                    <Stack gap="sm">
                      <h3 className="font-heading text-heading-3 text-text">{step.title}</h3>

                      <p className="text-body text-text-muted">{step.description}</p>
                    </Stack>
                  </Stack>
                </Card>
              </li>
            ))}
          </ol>

          <Card padding="lg" variant="elevated">
            <div className="grid gap-8 md:grid-cols-2 md:gap-0">
              <Stack className="md:pr-8" gap="sm">
                <Badge variant="processing">Copy analysis</Badge>

                <h3 className="font-heading text-heading-3 text-text">
                  Understand what is already working.
                </h3>

                <p className="text-body text-text-muted">
                  Explore the copy structure, offer, persuasion pattern, objections, proof,
                  strategic gaps and complete transcription.
                </p>
              </Stack>

              <Stack
                className="border-t border-border pt-8 md:border-t-0 md:border-l md:pt-0 md:pl-8"
                gap="sm"
              >
                <Badge variant="success">Copy adaptation</Badge>

                <h3 className="font-heading text-heading-3 text-text">
                  Apply the strategy to your offer.
                </h3>

                <p className="text-body text-text-muted">
                  Combine the reference strategy with your product, audience, available proof,
                  restrictions and desired platform.
                </p>
              </Stack>
            </div>
          </Card>
        </Stack>
      </Container>
    </section>
  )
}
