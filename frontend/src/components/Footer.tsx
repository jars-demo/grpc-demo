import { ISSUES_URL, MAINTAINER, ORG_URL, REPO_URL } from '@/lib/site'

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm sm:grid-cols-3 sm:px-6">
        <div className="space-y-2">
          <p className="font-semibold">gRPC &amp; HTTPS</p>
          <p className="text-muted">
            An educational workshop. The services and certificates are for learning, not for
            production.
          </p>
        </div>
        <nav aria-label="Project" className="space-y-2">
          <p className="font-semibold">Project</p>
          <ul className="space-y-1.5 text-muted">
            <li>
              <a className="hover:text-text" href={REPO_URL}>
                Source code
              </a>
            </li>
            <li>
              <a className="hover:text-text" href={`${REPO_URL}/blob/main/CONTRIBUTING.md`}>
                Contributing
              </a>
            </li>
            <li>
              <a className="hover:text-text" href={ISSUES_URL}>
                Report an issue
              </a>
            </li>
            <li>
              <a className="hover:text-text" href="/docs/commands/">
                Command reference
              </a>
            </li>
          </ul>
        </nav>
        <div className="space-y-2">
          <p className="font-semibold">Maintainer</p>
          <p className="text-muted">
            Created and maintained by{' '}
            <a className="text-text underline underline-offset-4" href={MAINTAINER.url}>
              {MAINTAINER.name}
            </a>
            .
          </p>
          <p className="text-muted">
            Part of{' '}
            <a className="hover:text-text" href={ORG_URL}>
              JARS DEMO
            </a>
            , independent hands-on engineering labs. MIT licensed.
          </p>
        </div>
      </div>
    </footer>
  )
}
