import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'

const frequentlyAskedQuestions = [
  {
    question: 'What is the difference between analysis and adaptation?',
    answer:
      'Analysis explains how the original copy works, including its structure, offer, mechanism, proof, objections and gaps. Adaptation uses that analysis together with your offer profile to create a new script for your product.',
  },
  {
    question: 'Which files can I upload?',
    answer:
      'Kyrg Studio accepts supported video and audio formats shown by the upload interface. The file is validated before the job is created, and FFmpeg verifies whether the media can actually be processed.',
  },
  {
    question: 'What happens after I submit a file?',
    answer:
      'The file is saved temporarily, the job enters the processing queue and a worker performs transcription, copy analysis and, when requested, adaptation. The job page shows whether the work is waiting, running, completed or failed.',
  },
  {
    question: 'Can I close the browser while the job is running?',
    answer:
      'Yes. Processing happens in the background and does not depend on the browser remaining open. Closing the page does not cancel a job that has already been submitted.',
  },
  {
    question: 'What happens to the uploaded file?',
    answer:
      'The original video or audio is temporary. After the job reaches a completed or failed state, the worker removes the stored media. The structured result remains associated with the job.',
  },
  {
    question: 'Do I need to complete an offer profile?',
    answer:
      'Only for copy adaptation. Copy analysis can inspect the reference without information about another product. Adaptation needs your audience, offer, promise, proof, restrictions and other details to produce a relevant script.',
  },
  {
    question: 'Can Kyrg Studio invent proof, promises or offer details?',
    answer:
      'The adaptation workflow is instructed to use only the information and proof you provide. It also validates unsupported claims before producing the result. Because AI output can still require judgment, the final script should always be reviewed before publication.',
  },
] as const

/**
 * Answers common product, processing, and data-handling questions using native
 * disclosure elements that remain accessible without JavaScript state.
 */
export function FaqSection() {
  return (
    <section aria-labelledby="faq-title" className="py-20 sm:py-24 lg:py-32" id="faq">
      <Container>
        <div className="grid gap-12 lg:grid-cols-[0.75fr_1.25fr] lg:gap-20">
          <Stack className="max-w-xl" gap="md">
            <span className="font-mono text-meta uppercase text-action">Questions and answers</span>

            <h2 className="font-heading text-heading-2 text-text" id="faq-title">
              What to know before starting.
            </h2>

            <p className="text-body-lg text-text-muted">
              Clear answers about the workflow, uploaded files and the information required to
              produce a useful result.
            </p>
          </Stack>

          <div>
            {frequentlyAskedQuestions.map((item) => (
              <details className="group border-b border-border first:border-t" key={item.question}>
                <summary className="flex min-h-20 cursor-pointer list-none items-center justify-between gap-6 py-5 text-left [&::-webkit-details-marker]:hidden">
                  <span className="text-body font-semibold text-text">{item.question}</span>

                  <span aria-hidden="true" className="relative size-5 shrink-0 text-text-muted">
                    <span className="absolute top-1/2 left-0 h-px w-full -translate-y-1/2 bg-current" />
                    <span className="absolute top-0 left-1/2 h-full w-px -translate-x-1/2 bg-current transition-transform duration-(--duration-fast) group-open:rotate-90" />
                  </span>
                </summary>

                <p className="max-w-2xl pb-6 pr-10 text-body text-text-muted">{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </Container>
    </section>
  )
}
