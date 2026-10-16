// What each interface in this workshop actually runs on, layer by layer.
const STACKS = [
  {
    name: 'REST in this workshop',
    layers: [
      { label: 'JSON', note: 'self-describing text' },
      { label: 'HTTP/1.1', note: 'one request at a time per connection' },
      { label: 'TLS 1.3', note: 'port 8443 (8080 without TLS)', secure: true },
      { label: 'TCP', note: '' },
    ],
  },
  {
    name: 'gRPC in this workshop',
    layers: [
      { label: 'Protocol Buffers', note: 'binary, schema from .proto' },
      { label: 'HTTP/2', note: 'streams multiplexed on one connection' },
      { label: 'TLS 1.3 · ALPN h2', note: 'port 50051, mutual TLS on 50052', secure: true },
      { label: 'TCP', note: '' },
    ],
  },
]

export function ProtocolStack() {
  return (
    <figure aria-labelledby="stack-caption" className="grid gap-4 sm:grid-cols-2">
      {STACKS.map((stack) => (
        <div key={stack.name} className="rounded-xl border border-line bg-bg p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
            {stack.name}
          </p>
          <ol className="space-y-1.5">
            {stack.layers.map((layer) => (
              <li
                key={layer.label}
                className={`rounded-lg border px-3 py-2 ${
                  layer.secure ? 'border-accent/40 bg-accent-soft' : 'border-line bg-surface'
                }`}
              >
                <span className="block font-mono text-sm font-medium">{layer.label}</span>
                {layer.note && <span className="block text-xs text-muted">{layer.note}</span>}
              </li>
            ))}
          </ol>
        </div>
      ))}
      <figcaption id="stack-caption" className="text-xs text-muted sm:col-span-2">
        Same business logic, two protocol stacks. HTTPS is HTTP inside TLS; HTTP/2 is a protocol
        version, not a synonym for HTTPS. Protocol Buffers encode data - they do not encrypt it.
      </figcaption>
    </figure>
  )
}
