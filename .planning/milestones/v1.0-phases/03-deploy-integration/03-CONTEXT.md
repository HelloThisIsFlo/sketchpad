# Phase 3: Deploy + Integration - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy the MCP server to Kubernetes, make it reachable over HTTPS via Cloudflare Tunnel at `thehome-sketchpad.kempenich.dev`, and confirm Claude AI (via Claude Code CLI and phone) completes the full OAuth handshake and can call both file tools. Includes consolidated documentation with setup guides and a local Claude Code test skill.

</domain>

<decisions>
## Implementation Decisions

### Deploy Workflow
- Makefile with targets: `make build`, `make push`, `make deploy`, `make all`
- Image tags: short git SHA for traceability + `latest` floating tag (both pushed on `make push`)
- `make deploy` applies manifests AND waits for rollout status (`kubectl rollout status`) — immediate feedback
- K8s manifests live in `k8s/` directory at project root (one file per resource: `k8s/deployment.yaml`, `k8s/service.yaml`, etc.)

### Documentation
- All guides consolidated under `docs/` directory
- Index: `docs/README.md` with Quick Start section (all commands, no explanation) at top, followed by numbered guide list
- Five numbered guides matching setup sequence:
  1. `docs/01-synology-nfs.md` — Synology NFS setup (from Phase 1)
  2. `docs/02-github-oauth-app.md` — GitHub OAuth App creation (from Phase 1)
  3. `docs/03-cloudflare-tunnel.md` — Cloudflare Tunnel configuration (from Phase 1)
  4. `docs/04-deploy.md` — Deploy server to K8s (new in Phase 3)
  5. `docs/05-claude-ai-setup.md` — Claude AI integration setup (new in Phase 3)
- Claude AI setup guide: brief steps (not tap-by-tap), covers both CLI and phone, includes troubleshooting section for common OAuth failures

### Verification Strategy
- Layer-by-layer deployment and verification:
  1. Apply K8s manifests, verify pod Running
  2. Curl health endpoint through Cloudflare Tunnel
  3. Run `test-oauth.sh` against live URL (adapted from Phase 2's local version — accepts server URL parameter)
  4. Test from Claude Code CLI via local test skill
  5. Test from Claude AI on phone
- Local Claude Code test skill (`.claude/skills/test-sketchpad`) with guided walkthrough — walks through each test step interactively: read, write, read-back, reporting what's happening at each step
- Each verification layer builds confidence before the next; failures are easier to localize

### Known Bug Handling
- Try first, patch if broken — both FastMCP DCR grant_types bug (#2460) and RFC 9728 protected-resource metadata bug (#1052)
- Minor issues: in-place workaround in our code with TODO comment referencing the upstream issue
- Fundamental/showstopper issues: debug thoroughly, investigate root cause, escalate to FastMCP GitHub — do NOT maintain patches for a framework we don't deeply understand
- The spike exists to prove the chain works, not to become a FastMCP maintainer

### Claude's Discretion
- K8s Deployment resource limits, replicas, health probe configuration
- Exact Makefile structure and variable naming
- test-oauth.sh adaptation details (parameterization approach)
- Test skill prompt wording and step descriptions
- Quick Start section exact commands and formatting
- Deploy guide (docs/04-deploy.md) structure and detail level

</decisions>

<specifics>
## Specific Ideas

- "I don't want to be maintaining hacks for a project I don't even understand" — if FastMCP is fundamentally broken, escalate rather than fork/patch. The spike proves the chain, it doesn't fix someone else's framework
- Quick-start section in docs index for repeat deployments — "all commands in order for someone who's done it before"
- Local Claude Code skill as test harness — `/test-sketchpad` invokes a guided walkthrough instead of manual chat testing
- Layer-by-layer verification mirrors the network stack: K8s → Tunnel → OAuth → Claude integration

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — no code exists yet (Phases 1 and 2 not executed)

### Established Patterns
- From Phase 1 context: NFS-backed PVC on Synology NAS, K8s Secrets for credentials, cloudflared as ingress
- From Phase 2 context: FastMCP with GitHubProvider, uv for dependency management, .env locally / K8s Secrets in production, test-oauth.sh for OAuth endpoint testing, Dockerfile built in Phase 2

### Integration Points
- Phase 1 delivers: K8s namespace, NFS StorageClass + PVC, cloudflared deployment, Secrets, reachable HTTPS endpoint
- Phase 2 delivers: Python server code with Dockerfile, test-oauth.sh, .env.example
- Phase 3 creates: K8s Deployment + Service manifests, Makefile, docs/ folder, Claude Code test skill
- Container registry: ghcr.io (public repo)
- Public hostname: `thehome-sketchpad.kempenich.dev`

### Known Issues to Handle
- FastMCP DCR grant_types bug (issue #2460) — try first, workaround if needed
- RFC 9728 protected-resource metadata bug (issue #1052) — try first, workaround if needed
- Claude.ai web has known `about:blank` bug (issue #11814) — use Claude Code CLI as primary test client

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-deploy-integration*
*Context gathered: 2026-03-03*
