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

/**
 * Public navigation displayed at the top of marketing pages.
 */
export function MarketingHeader() {
  return (
    <header className="border-b border-border bg-background">
      <Container>
        <nav
          aria-label="Main navigation"
          className="flex min-h-16 items-center justify-between"
        >
            <Link
                className="flex items-center gap-2 font-heading text-xl font-semibold text-text"
                to="/"
            >
                <img
                    src="/kyrglogo.png"
                    alt=""
                    aria-hidden="true"
                    className="size-9 object-contain"
                />

                <span>Kyrg Studio</span>
            </Link>
            <div className="hidden items-center gap-8 md:flex">
                <a
                    className="text-label text-text-muted transition-colors hover:text-text"
                    href="#how-it-works"
                >
                    How it works
                </a>

                <a
                    className="text-label text-text-muted transition-colors hover:text-text"
                    href="#features"
                >
                    Features
                </a>

                <a
                    className="text-label text-text-muted transition-colors hover:text-text"
                    href="#faq"
                >
                    FAQ
                </a>
            </div>

            <div className="hidden items-center gap-3 md:flex">
                <Link
                    className="px-3 py-2 text-label text-text-muted transition-colors hover:text-text"
                    to="/login"
                >
                    Log in
                </Link>

                <Link
                    className="rounded-md bg-action px-4 py-2.5 text-label text-text-inverse transition-colors hover:bg-action-hover"
                    to="/register"
                >
                    Create account
                </Link>
            </div>

            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <IconButton
                    aria-label="Open navigation menu"
                    className="md:hidden"
                    size="sm"
                    variant="ghost"
                    >
                    <MenuIcon />
                    </IconButton>
                </DropdownMenuTrigger>

                <DropdownMenuContent align="end">
                    <DropdownMenuItem asChild>
                    <a href="#how-it-works">How it works</a>
                    </DropdownMenuItem>

                    <DropdownMenuItem asChild>
                    <a href="#features">Features</a>
                    </DropdownMenuItem>

                    <DropdownMenuItem asChild>
                    <a href="#faq">FAQ</a>
                    </DropdownMenuItem>

                    <DropdownMenuSeparator />

                    <DropdownMenuItem asChild>
                    <Link to="/login">Log in</Link>
                    </DropdownMenuItem>

                    <DropdownMenuItem asChild>
                    <Link to="/register">Create account</Link>
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
    <svg
      aria-hidden="true"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}