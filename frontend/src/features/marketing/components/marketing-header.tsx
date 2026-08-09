import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '@/shared/components/language-switcher'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'

import { IconButton } from '@/shared/ui/icon-button'

import { Link } from 'react-router'

import { Container } from '@/shared/ui/container'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faRightToBracket } from '@fortawesome/free-solid-svg-icons'
import {faScrewdriverWrench} from '@fortawesome/free-solid-svg-icons'
import { faCircleQuestion } from '@fortawesome/free-solid-svg-icons'

/**
 * Public navigation displayed at the top of marketing pages.
 */
export function MarketingHeader() {
  const { t } = useTranslation()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur-md">
      <Container>
        <nav aria-label={t('marketing.header.mainNavigation')} className="flex min-h-16 items-center justify-between">
          <Link
            className="flex items-center gap-2 font-heading text-xl font-semibold text-text"
            to="/"
          >
            <img src="/kyrglogo.png" alt="" aria-hidden="true" className="size-9 object-contain" />

            <span>Kyrg Studio</span>
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            <a
              className="text-label text-text-muted transition-colors hover:text-text"
              href="#how-it-works"
            >
              {t("marketing.header.howItWorks")}
            </a>

            <a
              className="flex items-center gap-2 text-label text-text-muted transition-colors hover:text-text"
              href="#features"
            >
               <FontAwesomeIcon icon={faScrewdriverWrench} />
              {t("marketing.header.features")}
            </a>

            <a className="flex items-center gap-2 text-label text-text-muted transition-colors hover:text-text" href="#faq">
              <FontAwesomeIcon icon={faCircleQuestion} />
              {t("marketing.header.faq")}
            </a>
          </div>

          <div className="hidden items-center gap-3 md:flex">
             <LanguageSwitcher />

            <Link
              className="flex items-center gap-2 px-3 py-2 text-label text-text-muted transition-colors hover:text-text"
              to="/login"
            >
              <FontAwesomeIcon icon={faRightToBracket} />
              {t("marketing.header.login")}
            </Link>

            <Link
              className="flex items-center gap-2 rounded-md bg-action px-4 py-2.5 text-label text-text-inverse transition-colors hover:bg-action-hover"
              to="/register"
            >
              {t("marketing.header.register")}
            </Link>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <IconButton
                aria-label={t("marketing.header.openMenu")}
                className="md:hidden"
                size="sm"
                variant="ghost"
              >
                <MenuIcon />
              </IconButton>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <a href="#how-it-works">{t("marketing.header.howItWorks")}</a>
              </DropdownMenuItem>

              <DropdownMenuItem asChild>
                <a href="#features">{t("marketing.header.features")}</a>
              </DropdownMenuItem>

              <DropdownMenuItem asChild>
                <a href="#faq">{t("marketing.header.faq")}</a>
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem asChild>
                <Link to="/login">{t("marketing.header.login")}</Link>
              </DropdownMenuItem>

              <DropdownMenuItem asChild>
                <Link to="/register">{t("marketing.header.register")}</Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </Container>
    </header>
  )
}

function MenuIcon() {
  return (
    <svg aria-hidden="true" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}
