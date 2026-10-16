export const SITE_URL = 'https://grpc.jishanahmed.in'
export const REPO_URL = 'https://github.com/jars-demo/grpc-demo'
export const ISSUES_URL = `${REPO_URL}/issues`
export const ORG_URL = 'https://github.com/jars-demo'
export const MAINTAINER = { name: 'Jishanahmed AR Shaikh (JARS)', url: 'https://jishanahmed.in' }

export const TITLE = 'gRPC & HTTPS'
export const TAGLINE = 'From Requests to Secure RPC.'
export const DESCRIPTION =
  'Understand how HTTP, TLS, HTTP/2, and gRPC work together. Build a real service, secure the connection, and learn to diagnose the failures that matter.'

// Reference pages rendered from docs/*.md at the repository root.
export const DOCS = [
  { slug: 'architecture', title: 'Architecture' },
  { slug: 'security', title: 'Security' },
  { slug: 'troubleshooting', title: 'Troubleshooting' },
  { slug: 'commands', title: 'Commands' },
] as const

export type DocSlug = (typeof DOCS)[number]['slug']
