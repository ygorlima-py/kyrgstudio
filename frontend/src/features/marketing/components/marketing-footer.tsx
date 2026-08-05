import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Container } from '@/shared/ui/container'
import { Separator } from '@/shared/ui/separator'
import { Stack } from '@/shared/ui/stack'

/**
 * Provides public product navigation and account access at the end of every
 * marketing page.
 */
export function MarketingFooter() {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-border bg-background">
      <Container>
        <div className="grid gap-12 py-12 md:grid-cols-[1.4fr_1fr] lg:py-16">
          <Stack className="max-w-md" gap="md">
            <Link
              className="w-fit font-heading text-2xl font-semibold text-text"
              to="/"
            >
              Kyrg Studio
            </Link>

            <p className="text-body text-text-muted">
              {t('marketing.footer.description')}
            </p>

            <p className="font-mono text-meta uppercase text-text-subtle">
              {t('marketing.footer.meta.analysis')} ·{' '}
              {t('marketing.footer.meta.adaptation')} ·{' '}
              {t('marketing.footer.meta.structuredOutput')}
            </p>
          </Stack>

          <nav
            aria-label={t('marketing.footer.navigationLabel')}
            className="grid grid-cols-2 gap-8"
          >
            <Stack gap="sm">
              <p className="font-mono text-meta uppercase text-text-subtle">
                {t('marketing.footer.product.title')}
              </p>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#product-preview"
              >
                {t('marketing.footer.product.preview')}
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#how-it-works"
              >
                {t('marketing.footer.product.howItWorks')}
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#features"
              >
                {t('marketing.footer.product.features')}
              </a>

              <a
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                href="#faq"
              >
                {t('marketing.footer.product.faq')}
              </a>
            </Stack>

            <Stack gap="sm">
              <p className="font-mono text-meta uppercase text-text-subtle">
                {t('marketing.footer.account.title')}
              </p>

              <Link
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                to="/login"
              >
                {t('marketing.footer.account.login')}
              </Link>

              <Link
                className="w-fit text-body-sm text-text-muted transition-colors hover:text-text"
                to="/register"
              >
                {t('marketing.footer.account.createAccount')}
              </Link>
            </Stack>
          </nav>
        </div>

        <Separator decorative />

        <div
          className={[
            'flex flex-col gap-3 py-6 text-body-sm text-text-subtle',
            'sm:flex-row sm:items-center sm:justify-between',
          ].join(' ')}
        >
          <p>
            {t('marketing.footer.copyright', {
              year: currentYear,
            })}
          </p>

          <p>{t('marketing.footer.closingMessage')}</p>
        </div>
      </Container>
    </footer>
  )
}