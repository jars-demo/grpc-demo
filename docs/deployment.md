# Deploying the website

Only the **website** is deployed publicly. The gRPC and REST services, the certificates and the challenge are meant to run on each learner's own machine and are **never** deployed with the site. The site is a static export: HTML, CSS, JavaScript, no server code, no secrets, no access to `certs/out/`.

## Status

As of this writing the site is **not yet deployed**: no Vercel project or DNS record has been created from this repository. The steps below are what remains.

## Vercel (target: `grpc.jishanahmed.in`)

1. **Import the repository** in Vercel: *Add New → Project → Import* `jars-demo/grpc-demo`.
2. **Root Directory:** `frontend`. Keep *Include source files outside of the Root Directory in the Build Step* **enabled** - the build reads `../workshop`, `../docs` and `../challenge/scenarios`.
3. **Framework, build and output** come from `frontend/vercel.json`: install `npm ci`, build `npm run build`, output `out/`, plus security headers (CSP, `nosniff`, `frame-ancestors 'none'`). Node.js version: 22.x (from `package.json` `engines`).
4. **Environment variables:** none.
5. Deploy and check the preview URL: home page, `/workshop/`, a chapter, `/docs/architecture/` (five diagrams render), dark and light themes.
6. **Domain:** *Settings → Domains → Add* `grpc.jishanahmed.in`. Vercel shows the DNS record to create; for a subdomain this is normally a `CNAME` from `grpc` to the target Vercel displays (commonly `cname.vercel-dns.com`). Create it at the DNS provider of `jishanahmed.in`, wait for verification, and let Vercel issue the certificate.
7. Confirm `https://grpc.jishanahmed.in/sitemap.xml` and `/robots.txt` reference the right domain (`SITE_URL` in `frontend/src/lib/site.ts`).

No deployment credentials are stored in this repository or needed by CI. Vercel's Git integration builds previews for pull requests on its own.

## Any static host

```bash
cd frontend
npm ci
npm run build          # writes frontend/out/
```

Upload `frontend/out/` to any static host. Configure: trailing-slash URLs (`/workshop/` serves `/workshop/index.html`), `404.html` as the not-found page, and the headers from `frontend/nginx.conf`.

## Locally, in Docker

The `web` service in `docker-compose.yml` builds the same static site and serves it with unprivileged nginx on <http://localhost:3000>.

## Updating content

Chapters and docs are read at build time, so editing `workshop/*.md` or `docs/*.md` and merging to `main` is enough; the next build publishes them. CI builds the site on every pull request.
