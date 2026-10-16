import type { ReactNode } from 'react'

export function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id: string
  eyebrow: string
  title: string
  intro?: ReactNode
  children: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-20 py-16 sm:py-20">
      <p className="text-sm font-medium text-muted">{eyebrow}</p>
      <h2 id={`${id}-title`} className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
        {title}
      </h2>
      {intro && <div className="mt-3 max-w-2xl text-muted">{intro}</div>}
      <div className="mt-8">{children}</div>
    </section>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-line bg-bg p-5 ${className}`}>{children}</div>
}

export function ButtonLink({
  href,
  children,
  variant = 'primary',
}: {
  href: string
  children: ReactNode
  variant?: 'primary' | 'secondary'
}) {
  const style =
    variant === 'primary'
      ? 'bg-text text-bg hover:opacity-85'
      : 'border border-line text-text hover:border-accent hover:text-accent'
  return (
    <a
      href={href}
      className={`inline-flex items-center rounded-lg px-4 py-2.5 text-sm font-medium transition ${style}`}
    >
      {children}
    </a>
  )
}
