# ADR-0015: Host the static site on GitHub Pages; block merges with a ruleset

- **Status:** Accepted (2026-11-27, with the approved plan of feature 003, `web-foundation`). Supersedes the frontend part of the Hosting row in [ADR-0002](0002-technology-stack.md) ("Cloudflare Pages or Vercel"). The Phase 2 API host is still chosen in Phase 2.
- **Date:** 2026-11-27

## Context

Phase 1 ships a static site ([ADR-0001](0001-static-first-delivery.md)). ADR-0002 named Cloudflare Pages or Vercel and asked for the choice to be confirmed against current terms when it was made. Two more needs arose:
- **Merge blocking:** the constitution requires automated checks, and the web-foundation spec requires failed checks to block merges to `main`.
- **Publishing:** the owner published the code as the public repository `chrisbarreras/travel-check` (all rights reserved), keeping the earlier repository private.

## Decision

- **Hosting:** the frontend is deployed to GitHub Pages, as a project site at `https://chrisbarreras.github.io/travel-check/`. The deploy job uses the official `actions/upload-pages-artifact` and `actions/deploy-pages` actions, authenticated by the workflow's short-lived OIDC token, after the required checks pass on `main`.
- **Merge blocking:** a repository ruleset on `main` requires a pull request and the status checks `checks` (pipeline), `web-checks`, `web-browser` and `web-lighthouse`, and blocks force pushes and deletion.

## Consequences

- **No extra account or stored secret.** A failed deployment leaves the previous site live.
- **Free only while the repository is public.** Both Pages and rulesets need either a public repository or a paid GitHub plan.
- **Fixed caching.** GitHub Pages sets `Cache-Control: max-age=600` and can't be configured. That doesn't matter for the placeholder page, but revisit it if repeat-visit performance matters once the map arrives. Cloudflare Pages remains the alternative.
- **Required checks are matched by job name**, so web job names carry a `web-` prefix and run on every pull request without path filters.
