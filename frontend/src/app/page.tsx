import { CodeBlock } from '@/components/CodeBlock'
import { Footer } from '@/components/Footer'
import { Header } from '@/components/Header'
import { CertificateChain } from '@/components/landing/CertificateChain'
import { ProtocolStack } from '@/components/landing/ProtocolStack'
import { Mermaid } from '@/components/Mermaid'
import { ButtonLink, Card, Section } from '@/components/ui'
import { listChapters, listScenarios, readRepoFile } from '@/lib/content'
import { extractDiagram } from '@/lib/parse'
import { DESCRIPTION, ISSUES_URL, REPO_URL, TAGLINE, TITLE } from '@/lib/site'

// The learning path, each step linked to the chapter that teaches it.
const PATH = [
  { label: 'HTTP', chapter: '01-how-http-works' },
  { label: 'HTTPS', chapter: '02-https-and-tls' },
  { label: 'TLS', chapter: '02-https-and-tls' },
  { label: 'HTTP/2', chapter: '03-http2-fundamentals' },
  { label: 'Protocol Buffers', chapter: '04-protocol-buffers' },
  { label: 'gRPC', chapter: '05-first-grpc-call' },
  { label: 'Streaming', chapter: '07-grpc-streaming' },
  { label: 'Certificate validation', chapter: '09-certificate-validation' },
  { label: 'Mutual TLS', chapter: '10-mutual-tls' },
  { label: 'Troubleshooting', chapter: '11-debugging-clinic' },
]

const COMPARISON = [
  ['Addressing', 'POST /v1/greetings', 'WorkshopService/SayHello'],
  ['Payload', 'JSON text, readable without a schema', 'Protobuf binary, decoded with the .proto'],
  [
    'Contract',
    'Optional (OpenAPI, generated from code here)',
    'Required (.proto, code generated from it)',
  ],
  [
    'Errors',
    'HTTP status + JSON body (404, 422)',
    'gRPC status in trailers (NOT_FOUND, INVALID_ARGUMENT)',
  ],
  ['Streaming', 'Not built in', 'Server, client and bidirectional'],
  ['Browsers', 'Native', 'Needs gRPC-Web and a proxy'],
  ['Debugging', 'curl, any browser', 'Generated clients, grpcurl with the .proto'],
]

const FAILURES = [
  ['Untrusted issuer', 'CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate'],
  ['Hostname not in SAN', 'Hostname Verification Check failed'],
  ['Expired certificate', 'CERTIFICATE_VERIFY_FAILED: certificate has expired'],
  ['No client certificate', 'PEER_DID_NOT_RETURN_A_CERTIFICATE (server log)'],
  ['Authenticated, not authorized', 'PERMISSION_DENIED'],
]

const TOOLS = [
  ['Docker Desktop / Engine', 'Compose v2.20+', 'runs the services and this site'],
  ['uv', '0.5+', 'Python 3.13, clients, examples, tests'],
  ['OpenSSL', '1.1.1 or 3.x', 'certificates (or use the toolbox container)'],
  ['Node.js', '22', 'only to build the website yourself'],
]

const SETUP = `git clone ${REPO_URL}.git
cd grpc-demo
uv sync
uv run python certs/scripts/certs.py generate
uv run python scripts/tasks.py up
uv run python scripts/smoke_test.py`

const FIRST_CALLS = `uv run python examples/rest_client.py https://localhost:8443/v1/greetings --name Ada
uv run python -m grpc_client hello --name Ada
uv run python -m grpc_client --target localhost:50052 --cert certs/out/client.crt --key certs/out/client.key hello`

export default function Home() {
  const chapters = listChapters()
  const totalMinutes = chapters.reduce((sum, c) => sum + c.minutes, 0)
  const scenarios = listScenarios()
  const architecture = readRepoFile('docs', 'architecture.md')
  const tlsDiagram = extractDiagram(architecture, 'tls-trust')
  const grpcDiagram = extractDiagram(architecture, 'grpc-flow')

  return (
    <>
      <Header />
      <main id="main" className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* Hero */}
        <section className="grid gap-10 [&>*]:min-w-0 pb-6 pt-14 sm:pt-20 lg:grid-cols-[1.1fr_1fr] lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
              JARS DEMO · Hands-on workshop
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-6xl">{TITLE}</h1>
            <p className="mt-3 text-xl italic text-muted sm:text-2xl">{TAGLINE}</p>
            <p className="mt-6 max-w-xl text-lg leading-relaxed">{DESCRIPTION}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href={`/workshop/${chapters[0]?.slug ?? ''}/`}>
                Start the workshop
              </ButtonLink>
              <ButtonLink href="/docs/architecture/" variant="secondary">
                Explore the architecture
              </ButtonLink>
            </div>
            <p className="mt-6 text-sm text-muted">
              {chapters.length} chapters · about {Math.round(totalMinutes / 15) / 4} hours ·
              self-paced · runs entirely on your machine
            </p>
          </div>
          <ProtocolStack />
        </section>

        {/* Learning path */}
        <Section
          id="path"
          eyebrow="Learning path"
          title="Observe it, break it, fix it"
          intro="Each step builds on the last. You send real requests, read real bytes and certificates, trigger real failures, and verify the fix."
        >
          <ol className="flex flex-wrap items-center gap-2" aria-label="Topics in order">
            {PATH.map((step, i) => (
              <li key={step.label} className="flex items-center gap-2">
                <a
                  href={`/workshop/${step.chapter}/`}
                  className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm transition hover:border-accent hover:text-accent"
                >
                  {step.label}
                </a>
                {i < PATH.length - 1 && (
                  <span className="text-muted" aria-hidden="true">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
        </Section>

        {/* REST vs gRPC */}
        <Section
          id="compare"
          eyebrow="REST vs gRPC"
          title="One service, two front doors"
          intro={
            <>
              Both interfaces call the same Python functions, so the differences you measure are the
              protocols&rsquo;. Neither is universally faster: payload size, concurrency, connection
              reuse and implementation decide. Chapter 12 shows how to measure honestly.
            </>
          }
        >
          <div className="table-wrap">
            <table className="w-full text-sm">
              <thead className="bg-surface text-left">
                <tr>
                  <th scope="col" className="px-4 py-2.5 font-semibold">
                    &nbsp;
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">
                    REST (FastAPI, HTTP/1.1)
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">
                    gRPC (HTTP/2)
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map(([aspect, rest, grpc]) => (
                  <tr key={aspect} className="border-t border-line">
                    <th scope="row" className="px-4 py-2.5 text-left font-medium">
                      {aspect}
                    </th>
                    <td className="px-4 py-2.5 text-muted">{rest}</td>
                    <td className="px-4 py-2.5 text-muted">{grpc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Diagrams */}
        <Section
          id="flow"
          eyebrow="How it works"
          title="From handshake to RPC"
          intro="Rendered from the same Mermaid source as docs/architecture.md."
        >
          <div className="grid gap-6 [&>*]:min-w-0 lg:grid-cols-2">
            <div className="space-y-3">
              <h3 className="font-semibold">TLS: the handshake and the trust decision</h3>
              <p className="text-sm text-muted">
                The client checks four things before sending a single request: the chain leads to a
                CA it trusts, the hostname is in the certificate&rsquo;s SAN, the certificate is
                within its validity period, and the server holds the matching private key.
              </p>
              {tlsDiagram && (
                <Mermaid
                  source={tlsDiagram}
                  label="TLS 1.3 handshake: ClientHello with SNI and ALPN, ServerHello, server certificate and signature, client verification of chain, hostname, validity and key possession, then encrypted application data."
                />
              )}
            </div>
            <div className="space-y-3">
              <h3 className="font-semibold">gRPC: a call over HTTP/2</h3>
              <p className="text-sm text-muted">
                A generated stub serializes the request; the channel sends it as an HTTP/2 stream
                whose path names the method; the server routes it to your servicer; the status comes
                back in the trailers.
              </p>
              {grpcDiagram && (
                <Mermaid
                  source={grpcDiagram}
                  label="gRPC request flow: client code, generated stub, channel over TLS with ALPN h2, gRPC server, interceptor, servicer routed by path, domain logic, and the status returned in HTTP/2 trailers."
                />
              )}
            </div>
          </div>
        </Section>

        {/* Certificate lab */}
        <Section
          id="certificates"
          eyebrow="Certificate lab"
          title="Your own CA, and every way trust can fail"
          intro="Generate a local educational CA and certificates with OpenSSL, then break each verification check on purpose and read the real error."
        >
          <div className="grid gap-6 [&>*]:min-w-0 lg:grid-cols-[1.4fr_1fr]">
            <CertificateChain />
            <div className="space-y-4">
              <CodeBlock
                lang="bash"
                code={`uv run python certs/scripts/certs.py generate
uv run python certs/scripts/certs.py inspect server
uv run python certs/scripts/certs.py verify
uv run python certs/scripts/certs.py rotate server`}
              />
              <ul className="space-y-2 text-sm">
                {FAILURES.map(([name, error]) => (
                  <li key={name} className="rounded-lg border border-line px-3 py-2">
                    <span className="font-medium">{name}</span>
                    <code className="mt-0.5 block break-words font-mono text-xs text-muted">
                      {error}
                    </code>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Section>

        {/* Chapters */}
        <Section
          id="chapters"
          eyebrow="Curriculum"
          title={`${chapters.length} chapters, about ${Math.round(totalMinutes / 15) / 4} hours`}
          intro="Every chapter has objectives, exact commands, the output to expect, a common failure to diagnose, and a knowledge check."
        >
          <ol className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2">
            {chapters.map((c) => (
              <li key={c.slug} className="bg-bg">
                <a
                  href={`/workshop/${c.slug}/`}
                  className="flex h-full gap-3 p-4 transition hover:bg-surface"
                >
                  <span className="font-mono text-xs text-accent">{c.number}</span>
                  <span className="flex-1">
                    <span className="block font-medium">{c.title}</span>
                    <span className="block text-sm text-muted">{c.summary}</span>
                  </span>
                  <span className="whitespace-nowrap text-xs text-muted">{c.minutes} min</span>
                </a>
              </li>
            ))}
          </ol>
        </Section>

        {/* Setup */}
        <Section
          id="setup"
          eyebrow="Get started"
          title="Prerequisites and local setup"
          intro="Everything runs locally: no cloud account, no API keys. Commands work in PowerShell, bash and zsh. You run them in your terminal - nothing on this site executes on your machine."
        >
          <div className="grid gap-6 [&>*]:min-w-0 lg:grid-cols-2">
            <div className="table-wrap">
              <table className="w-full text-sm">
                <thead className="bg-surface text-left">
                  <tr>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Tool
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      Version
                    </th>
                    <th scope="col" className="px-4 py-2.5 font-semibold">
                      For
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {TOOLS.map(([tool, version, purpose]) => (
                    <tr key={tool} className="border-t border-line">
                      <td className="px-4 py-2.5 font-medium">{tool}</td>
                      <td className="px-4 py-2.5 text-muted">{version}</td>
                      <td className="px-4 py-2.5 text-muted">{purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="space-y-4">
              <CodeBlock lang="bash" code={SETUP} />
              <p className="text-sm text-muted">Then your first REST, gRPC and mutual TLS calls:</p>
              <CodeBlock lang="bash" code={FIRST_CALLS} />
            </div>
          </div>
        </Section>

        {/* Final challenge */}
        <Section
          id="challenge"
          eyebrow="Final challenge"
          title="Repair six broken secure connections"
          intro="Each scenario is a real misconfigured client against real servers. Reproduce the failure, read the error, inspect, fix the profile, and verify. The checker also rejects fixes that weaken security."
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {scenarios.map((s) => (
              <Card key={s.number}>
                <p className="font-mono text-xs text-accent">Scenario {s.number}</p>
                <p className="mt-1 font-medium">{s.title}</p>
              </Card>
            ))}
          </div>
          <div className="mt-6">
            <ButtonLink href="/workshop/13-final-challenge/" variant="secondary">
              Open the challenge
            </ButtonLink>
          </div>
        </Section>

        {/* Contribute */}
        <Section id="contribute" eyebrow="Open source" title="Contribute">
          <div className="grid gap-3 sm:grid-cols-3">
            <Card>
              <a className="font-medium hover:text-accent" href={REPO_URL}>
                Source code
              </a>
              <p className="mt-1 text-sm text-muted">MIT licensed, on GitHub.</p>
            </Card>
            <Card>
              <a
                className="font-medium hover:text-accent"
                href={`${REPO_URL}/blob/main/CONTRIBUTING.md`}
              >
                Contribution guide
              </a>
              <p className="mt-1 text-sm text-muted">Setup, checks, and how chapters are tested.</p>
            </Card>
            <Card>
              <a className="font-medium hover:text-accent" href={ISSUES_URL}>
                Report an issue
              </a>
              <p className="mt-1 text-sm text-muted">A command that did not work? Tell us.</p>
            </Card>
          </div>
        </Section>
      </main>
      <Footer />
    </>
  )
}
