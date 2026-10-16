import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { ButtonLink } from '@/components/ui'

export default function NotFound() {
  return (
    <>
      <Header />
      <main id="main" className="mx-auto max-w-2xl px-4 py-24 text-center sm:px-6">
        <p className="font-mono text-sm text-accent">404 · NOT_FOUND</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">This page does not exist</h1>
        <p className="mt-3 text-muted">
          In gRPC this would be <code className="font-mono">NOT_FOUND</code>; in REST, a 404. Either
          way, the request needs to change, not be retried.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <ButtonLink href="/workshop/">Go to the workshop</ButtonLink>
          <ButtonLink href="/" variant="secondary">
            Home
          </ButtonLink>
        </div>
      </main>
      <Footer />
    </>
  )
}
