import { REPO_URL } from '@/lib/site'

import { Logo } from './Logo'
import { ThemeToggle } from './ThemeToggle'

const NAV = [
  { href: '/workshop/', label: 'Workshop' },
  { href: '/docs/architecture/', label: 'Architecture' },
  { href: '/docs/security/', label: 'Security' },
  { href: '/docs/troubleshooting/', label: 'Troubleshooting' },
]

export function Header({ current }: { current?: string }) {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <a href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Logo />
          <span>gRPC &amp; HTTPS</span>
        </a>
        <nav aria-label="Main" className="ml-auto flex items-center gap-1 text-sm">
          <div className="hidden items-center gap-1 sm:flex">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                aria-current={current === item.href ? 'page' : undefined}
                className="rounded-md px-2.5 py-1.5 text-muted transition hover:text-text aria-[current=page]:text-text aria-[current=page]:font-medium"
              >
                {item.label}
              </a>
            ))}
          </div>
          <a
            href="/workshop/"
            className="rounded-md px-2.5 py-1.5 text-muted hover:text-text sm:hidden"
          >
            Workshop
          </a>
          <a
            href={REPO_URL}
            className="rounded-md px-2.5 py-1.5 text-muted transition hover:text-text"
            target="_blank"
            rel="noreferrer"
          >
            GitHub<span className="sr-only"> (opens in a new tab)</span>
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
