// The certificates certs.py generates and who trusts what. Mirrors docs/security.md.
function Cert({
  file,
  cn,
  detail,
  tone = 'trusted',
}: {
  file: string
  cn: string
  detail: string
  tone?: 'ca' | 'trusted' | 'untrusted' | 'expired'
}) {
  const tones = {
    ca: 'border-accent bg-accent-soft',
    trusted: 'border-line bg-bg',
    untrusted: 'border-dashed border-bad/60 bg-bg',
    expired: 'border-dashed border-warn/70 bg-bg',
  }
  return (
    <div className={`rounded-lg border px-3 py-2 ${tones[tone]}`}>
      <p className="font-mono text-xs font-semibold">{file}</p>
      <p className="text-sm">{cn}</p>
      <p className="text-xs text-muted">{detail}</p>
    </div>
  )
}

export function CertificateChain() {
  return (
    <figure aria-labelledby="chain-caption" className="space-y-3">
      <div className="grid gap-3 md:grid-cols-[1fr_auto_2fr] md:items-center">
        <Cert
          file="ca.crt"
          cn="JARS Workshop Local CA"
          detail="CA:TRUE · trusted by every client and server"
          tone="ca"
        />
        <span className="hidden text-center text-muted md:block" aria-hidden="true">
          signs →
        </span>
        <div className="grid gap-2 sm:grid-cols-2">
          <Cert
            file="server.crt"
            cn="grpc-server"
            detail="SAN: localhost, grpc-server, rest-https"
          />
          <Cert
            file="client.crt"
            cn="workshop-client"
            detail="clientAuth · authenticated, not admin"
          />
          <Cert
            file="admin.crt"
            cn="workshop-admin"
            detail="clientAuth · authorized for AdminService"
          />
          <Cert
            file="expired-server.crt"
            cn="grpc-expired"
            detail="valid Jan 1-31, 2024 only"
            tone="expired"
          />
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-[1fr_auto_2fr] md:items-center">
        <Cert
          file="rogue-ca.crt"
          cn="Rogue Untrusted CA"
          detail="nobody trusts it"
          tone="untrusted"
        />
        <span className="hidden text-center text-muted md:block" aria-hidden="true">
          signs →
        </span>
        <div className="grid gap-2 sm:grid-cols-2">
          <Cert
            file="rogue-client.crt"
            cn="workshop-client"
            detail="same name as client.crt - rejected"
            tone="untrusted"
          />
        </div>
      </div>
      <figcaption id="chain-caption" className="text-xs text-muted">
        Generated locally by <code className="font-mono">certs/scripts/certs.py</code> with OpenSSL.
        Never committed, never baked into images, never to be trusted outside the workshop.
      </figcaption>
    </figure>
  )
}
