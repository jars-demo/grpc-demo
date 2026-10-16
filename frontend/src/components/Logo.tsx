// Two endpoints joined by a secured channel: the workshop in one mark.
export function Logo({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect x="1" y="1" width="30" height="30" rx="8" fill="var(--text)" />
      <circle cx="9.5" cy="16" r="3.2" fill="var(--bg)" />
      <circle cx="22.5" cy="16" r="3.2" fill="var(--bg)" />
      <path
        d="M12.7 13.2h6.6M12.7 18.8h6.6"
        stroke="var(--bg)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}
