import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Container } from '@/shared/ui/container'
import { Inline } from '@/shared/ui/inline'
import { Separator } from '@/shared/ui/separator'
import { Stack } from '@/shared/ui/stack'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/shared/ui/tabs'

const analysisSections = [
  {
    order: '01',
    type: 'Hook',
    summary: 'Interrupts the expected belief and opens a curiosity gap.',
  },
  {
    order: '02',
    type: 'Problem',
    summary: 'Connects the audience frustration to the central problem.',
  },
  {
    order: '03',
    type: 'Mechanism',
    summary: 'Introduces the explanation behind the proposed solution.',
  },
  {
    order: '04',
    type: 'Proof',
    summary: 'Supports the promise with available evidence.',
  },
  {
    order: '05',
    type: 'CTA',
    summary: 'Directs the viewer toward the next action.',
  },
] as const

const adaptedSections = [
  {
    order: '01',
    type: 'Hook',
    text: 'You do not need more vocabulary. You need to stop translating every sentence before you speak.',
  },
  {
    order: '02',
    type: 'Problem',
    text: 'That mental translation is why conversations feel slow, stressful and unnatural.',
  },
  {
    order: '03',
    type: 'Mechanism',
    text: 'The method trains complete responses through situations you actually experience.',
  },
  {
    order: '04',
    type: 'Proof',
    text: 'The script uses only the verified student experience provided in the offer profile.',
  },
] as const

/**
 * Demonstrates the structured outputs produced by copy analysis and adaptation.
 *
 * The preview uses static public examples and never loads job or user data.
 */
export function ProductPreview() {
  return (
    <section
      aria-labelledby="product-preview-title"
      className="py-20 sm:py-24 lg:py-32"
      id="product-preview"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <Badge variant="action">Product preview</Badge>

            <h2
              className="font-heading text-heading-2 text-text"
              id="product-preview-title"
            >
              From raw video to structured creative intelligence.
            </h2>

            <p className="text-body-lg text-text-muted">
              Explore how Kyrg Studio organizes the strategy inside a reference
              copy and transforms it into an editable script for another offer.
            </p>
          </Stack>

          <Tabs defaultValue="analysis">
            <TabsList aria-label="Product output preview">
              <TabsTrigger value="analysis">Copy analysis</TabsTrigger>
              <TabsTrigger value="adaptation">Adapted script</TabsTrigger>
            </TabsList>

            <TabsContent value="analysis">
              <AnalysisPreview />
            </TabsContent>

            <TabsContent value="adaptation">
              <AdaptationPreview />
            </TabsContent>
          </Tabs>
        </Stack>
      </Container>
    </section>
  )
}

function AnalysisPreview() {
  return (
    <Card className="overflow-hidden" padding="none" variant="elevated">
      <div className="border-b border-border p-5 sm:p-6">
        <Inline justify="between">
          <Stack gap="xs">
            <span className="font-mono text-meta text-text-subtle">
              REFERENCE COPY
            </span>
            <h3 className="font-heading text-heading-3 text-text">
              Persuasion map
            </h3>
          </Stack>

          <Badge variant="processing">Analysis complete</Badge>
        </Inline>
      </div>

      <div className="grid lg:grid-cols-[1.15fr_0.85fr]">
        <Stack className="p-5 sm:p-6 lg:border-r lg:border-border" gap="sm">
          <span className="text-label text-text-muted">Copy structure</span>

          {analysisSections.map((section) => (
            <div
              className="grid gap-2 rounded-md border border-border bg-surface p-4 sm:grid-cols-[2rem_7rem_1fr] sm:items-center"
              key={section.order}
            >
              <span className="font-mono text-meta text-text-subtle">
                {section.order}
              </span>

              <span className="text-label text-text">{section.type}</span>

              <span className="text-body-sm text-text-muted">
                {section.summary}
              </span>
            </div>
          ))}
        </Stack>

        <Stack className="bg-surface-muted p-5 sm:p-6" gap="lg">
          <Stack gap="sm">
            <span className="text-label text-text-muted">Offer extracted</span>
            <p className="text-body text-text">
              A practical method that helps adults respond naturally in
              everyday English conversations.
            </p>
          </Stack>

          <Separator decorative />

          <Stack gap="sm">
            <span className="text-label text-text-muted">
              Strategic mechanism
            </span>
            <p className="text-body-sm text-text-muted">
              Conversation practice organized around real situations instead
              of isolated vocabulary.
            </p>
          </Stack>

          <Separator decorative />

          <Stack gap="sm">
            <Inline gap="sm">
              <Badge variant="warning">Gap detected</Badge>
              <span className="text-label text-text">Proof specificity</span>
            </Inline>

            <p className="text-body-sm text-text-muted">
              The reference makes a strong promise but needs clearer evidence
              before the same persuasion intensity can be adapted safely.
            </p>
          </Stack>
        </Stack>
      </div>
    </Card>
  )
}

function AdaptationPreview() {
  return (
    <Card className="overflow-hidden" padding="none" variant="elevated">
      <div className="border-b border-border p-5 sm:p-6">
        <Inline justify="between">
          <Stack gap="xs">
            <span className="font-mono text-meta text-text-subtle">
              ADAPTED OUTPUT
            </span>
            <h3 className="font-heading text-heading-3 text-text">
              Editable script
            </h3>
          </Stack>

          <Badge variant="success">Validated</Badge>
        </Inline>
      </div>

      <Stack className="p-5 sm:p-6" gap="sm">
        {adaptedSections.map((section) => (
          <div
            className="grid gap-3 rounded-md border border-border bg-surface p-4 sm:grid-cols-[2rem_7rem_1fr]"
            key={section.order}
          >
            <span className="font-mono text-meta text-text-subtle">
              {section.order}
            </span>

            <Badge variant="neutral">{section.type}</Badge>

            <p className="text-body text-text">{section.text}</p>
          </div>
        ))}

        <div className="mt-2 rounded-md bg-success-muted p-4">
          <p className="text-label text-success">Validation passed</p>
          <p className="mt-1 text-body-sm text-text-muted">
            The adapted script preserves the reference strategy without
            inventing proof, guarantees or commercial conditions.
          </p>
        </div>
      </Stack>
    </Card>
  )
}