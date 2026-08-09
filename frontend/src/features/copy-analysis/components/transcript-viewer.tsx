import { useTranslation } from 'react-i18next'

import type { NormalizedTranscription } from '../utils/normalize-analysis-result'

export interface TranscriptViewerProps {
  readonly transcription: NormalizedTranscription | null
}

/** Present the public transcription in a collapsible, long-form reading area. */
export function TranscriptViewer({ transcription }: TranscriptViewerProps) {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="transcript-heading">
      <div>
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('analysisResult.transcription.eyebrow')}
        </p>

        <h2 className="mt-2 font-heading text-heading-3 text-text" id="transcript-heading">
          {t('analysisResult.transcription.title')}
        </h2>

        <p className="mt-2 max-w-3xl text-body text-text-muted">
          {t('analysisResult.transcription.description')}
        </p>
      </div>

      {transcription ? (
        <details className="group mt-6 border-y border-border">
          <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-4 text-label text-text focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus [&::-webkit-details-marker]:hidden">
            <span>{t('analysisResult.transcription.viewFull')}</span>
            <span className="flex items-center gap-3">
              {transcription.language ? (
                <span className="font-mono text-meta uppercase text-text-subtle">
                  {transcription.language}
                </span>
              ) : null}
              <ChevronIcon />
            </span>
          </summary>

          <div className="max-h-[32rem] overflow-y-auto border-t border-border py-6 pr-3">
            <p className="max-w-4xl whitespace-pre-wrap text-body text-text">
              {transcription.text}
            </p>
          </div>
        </details>
      ) : (
        <p className="mt-6 border-y border-border py-7 text-body text-text-muted">
          {t('analysisResult.transcription.empty')}
        </p>
      )}
    </section>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 transition-transform duration-(--duration-fast) group-open:rotate-180"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="m4 6 4 4 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}
