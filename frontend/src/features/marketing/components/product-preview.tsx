import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Container } from '@/shared/ui/container'
import { Stack } from '@/shared/ui/stack'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'

interface ProductScreenshotProps {
  readonly alt: string
  readonly label: string
  readonly src: string
}

/**
 * Presents real product screenshots without exposing job or customer data.
 *
 * If the configured public asset cannot be loaded, the frame displays a
 * neutral placeholder instead of a broken image.
 */
function ProductScreenshot({ alt, label, src }: ProductScreenshotProps) {
  const [imageUnavailable, setImageUnavailable] = useState(false)

  return (
    <figure className="overflow-hidden rounded-xl border border-border bg-surface shadow-xl">
      <div className="bg-surface-muted">
        {imageUnavailable ? (
          <div
            aria-label={alt}
            className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-6 text-center"
            role="img"
          >
            <svg
              aria-hidden="true"
              className="size-10 text-text-subtle"
              fill="none"
              viewBox="0 0 48 48"
            >
              <rect
                height="34"
                rx="4"
                stroke="currentColor"
                strokeWidth="2"
                width="42"
                x="3"
                y="7"
              />
              <path
                d="m10 33 9-9 6 6 5-5 8 8"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
              <circle cx="33" cy="17" fill="currentColor" r="3" />
            </svg>

            <p className="text-label text-text-muted">{label}</p>
          </div>
        ) : (
          <img
            alt={alt}
            className="block h-auto w-full"
            decoding="async"
            loading="lazy"
            onError={() => setImageUnavailable(true)}
            src={src}
          />
        )}
      </div>
    </figure>
  )
}

/**
 * Shows public screenshots of the analysis and adaptation results.
 *
 * Screenshot files are selected from the active interface language and remain
 * static public assets; this section never loads private job data.
 */
export function ProductPreview() {
  const { t } = useTranslation()
  const analysisScreenshot = '/analysis_copy.png'
  const adaptationScreenshot = '/copy_adapted.png'

  return (
    <section
      aria-labelledby="product-preview-title"
      className="py-20 sm:py-24 lg:py-32"
      id="product-preview"
    >
      <Container>
        <Stack gap="xl">
          <Stack className="max-w-3xl" gap="md">
            <span className="inline-flex w-fit items-center rounded-pill bg-action px-3 py-1 text-label text-text-inverse">
              {t('marketing.preview.badge')}
            </span>

            <h2 className="font-heading text-heading-2 text-text" id="product-preview-title">
              {t('marketing.preview.title')}
            </h2>

            <p className="text-body-lg text-text-muted">{t('marketing.preview.description')}</p>
          </Stack>

          <Tabs defaultValue="analysis">
            <TabsList aria-label={t('marketing.preview.tabsLabel')}>
              <TabsTrigger value="analysis">{t('marketing.preview.analysisTab')}</TabsTrigger>
              <TabsTrigger value="adaptation">{t('marketing.preview.adaptationTab')}</TabsTrigger>
            </TabsList>

            <TabsContent value="analysis">
              <ProductScreenshot
                alt={t('marketing.preview.analysisImageAlt')}
                key={analysisScreenshot}
                label={t('marketing.preview.analysisTab')}
                src={analysisScreenshot}
              />
            </TabsContent>

            <TabsContent value="adaptation">
              <ProductScreenshot
                alt={t('marketing.preview.adaptationImageAlt')}
                key={adaptationScreenshot}
                label={t('marketing.preview.adaptationTab')}
                src={adaptationScreenshot}
              />
            </TabsContent>
          </Tabs>
        </Stack>
      </Container>
    </section>
  )
}
