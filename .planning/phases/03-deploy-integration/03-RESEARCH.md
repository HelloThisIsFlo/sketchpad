# Phase 3: Deploy + Integration - Research

**Researched:** 2026-03-04
**Domain:** Kubernetes deployment, Cloudflare Tunnel routing, Claude AI integration (CLI + mobile), documentation consolidation
**Confidence:** HIGH

## Summary

Phase 3 bridges the locally-validated MCP server (Phase 2) to production on Kubernetes and proves the full chain works with Claude AI as the client. The work decomposes into four domains: (1) K8s Deployment manifest + Makefile for the build/deploy workflow, (2) Cloudflare Tunnel re-routing from the placeholder to the real server, (3) Claude AI integration via both Claude Code CLI and claude.ai web connectors (which sync to mobile), and (4) documentation consolidation under `docs/` with a test skill for repeatable verification.

The codebase is already well-structured from Phases 1 and 2. The Dockerfile, GitHub Actions CI, K8s namespace, PVCs, Secrets, and cloudflared deployment all exist. The primary new artifacts are: a `k8s/deployment.yaml` for the real server, a `k8s/service.yaml` (replacing the placeholder's service definition), a `Makefile`, five numbered docs under `docs/`, and a Claude Code test skill at `.claude/skills/test-sketchpad/SKILL.md`.

**Primary recommendation:** Deploy layer-by-layer (K8s manifests -> health check -> OAuth test -> Claude Code CLI -> phone), verifying at each layer before proceeding. Use the existing `test_oauth.py` against the live URL as the automated OAuth validation step.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Makefile with targets: `make build`, `make push`, `make deploy`, `make all`
- Image tags: short git SHA for traceability + `latest` floating tag (both pushed on `make push`)
- `make deploy` applies manifests AND waits for rollout status (`kubectl rollout status`)
- K8s manifests live in `k8s/` directory at project root (one file per resource)
- All guides consolidated under `docs/` directory
- Index: `docs/README.md` with Quick Start section at top, followed by numbered guide list
- Five numbered guides: 01-synology-nfs, 02-github-oauth-app, 03-cloudflare-tunnel, 04-deploy, 05-claude-ai-setup
- Claude AI setup guide: brief steps, covers both CLI and phone, includes troubleshooting
- Layer-by-layer deployment verification (K8s -> Tunnel -> OAuth -> Claude CLI -> Phone)
- Local Claude Code test skill (`.claude/skills/test-sketchpad`) with guided walkthrough
- Known bug handling: try first, patch if broken; minor = in-place workaround with TODO; showstopper = escalate

### Claude's Discretion
- K8s Deployment resource limits, replicas, health probe configuration
- Exact Makefile structure and variable naming
- test-oauth.sh adaptation details (parameterization approach)
- Test skill prompt wording and step descriptions
- Quick Start section exact commands and formatting
- Deploy guide (docs/04-deploy.md) structure and detail level

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| E2E-01 | User can read the sketchpad from Claude AI on their phone | Claude.ai web connector setup syncs to mobile; test skill verifies read_file works; docs/05-claude-ai-setup.md covers phone steps |
| E2E-02 | User can write to the sketchpad from Claude AI on their phone | Same connector + sync; test skill verifies write_file + read-back; docs cover phone usage |
| E2E-03 | Data written in one conversation persists and is readable in a new conversation | NFS-backed PVC already proven in Phase 1; pod restart test (`kubectl rollout restart`) validates persistence |
| DOCS-01 | `docs/` folder exists with an index and step-by-step guides for all manual setup steps | Five numbered guides + README.md index with Quick Start; existing docs renamed/moved from flat structure |
| DOCS-04 | Guide for adding the server as a Claude AI Integration on phone | docs/05-claude-ai-setup.md covers both Claude Code CLI and claude.ai web connector (syncs to phone) |

</phase_requirements>

## Standard Stack

### Core (already exists from Phases 1-2)
| Component | Version/Detail | Purpose | Status |
|-----------|---------------|---------|--------|
| FastMCP | 3.1.0 | MCP server framework with OAuth | Installed, validated |
| Python | 3.12 | Runtime | Dockerfile uses python:3.12-slim |
| uv | latest | Dependency management | Used in Dockerfile builder stage |
| Kubernetes (Talos OS) | existing cluster | Container orchestration | Namespace `sketchpad` exists |
| Cloudflare Tunnel | cloudflared 2026.2.0 | HTTPS ingress | Deployed, routing to placeholder |
| ghcr.io | public | Container registry | CI pushes on every main push |

### New in Phase 3
| Component | Purpose | Why |
|-----------|---------|-----|
| Makefile | Build/deploy workflow | User decision: `make build`, `make push`, `make deploy`, `make all` |
| K8s Deployment manifest | Run the real MCP server | Replaces the nginx placeholder |
| K8s Service manifest | Route traffic to server pod | Updates targetPort from 80 to 8000 |
| Claude Code skill | Repeatable test harness | `/test-sketchpad` guided walkthrough |

### No New Dependencies
Phase 3 introduces no new Python dependencies or libraries. Everything needed is already installed from Phases 1 and 2.

## Architecture Patterns

### Current Codebase Structure (Phase 2 output)
```
sketchpad/
  .claude/
    settings.local.json
  .github/workflows/
    build.yaml           # CI: build + push to ghcr.io on push to main
  docs/
    synology-nfs.md      # -> will become 01-synology-nfs.md
    github-oauth-app.md  # -> will become 02-github-oauth-app.md
    cloudflare-tunnel.md # -> will become 03-cloudflare-tunnel.md
    google-oauth-app.md  # stays as supplementary doc
    local-development.md # stays as supplementary doc
    mcp-inspector.md     # stays as supplementary doc
  k8s/
    namespace.yaml
    pvc.yaml
    cloudflared/deployment.yaml
    placeholder/deployment.yaml  # contains ConfigMap + Deployment + Service
    secrets/README.md
  src/sketchpad/
    __init__.py
    __main__.py
    config.py
    server.py
    tools.py
  Dockerfile
  pyproject.toml
  test_oauth.py
  .env.example
```

### Target Structure (Phase 3 additions)
```
sketchpad/
  .claude/
    skills/
      test-sketchpad/
        SKILL.md            # NEW: guided test walkthrough
  docs/
    README.md               # NEW: index with Quick Start
    01-synology-nfs.md      # RENAMED from synology-nfs.md
    02-github-oauth-app.md  # RENAMED from github-oauth-app.md
    03-cloudflare-tunnel.md # RENAMED from cloudflare-tunnel.md
    04-deploy.md            # NEW: K8s deployment guide
    05-claude-ai-setup.md   # NEW: Claude AI integration setup
    google-oauth-app.md     # stays (supplementary)
    local-development.md    # stays (supplementary)
    mcp-inspector.md        # stays (supplementary)
  k8s/
    deployment.yaml          # NEW: real MCP server Deployment
    service.yaml             # NEW: updated Service (targetPort 8000)
    namespace.yaml
    pvc.yaml
    cloudflared/deployment.yaml
    placeholder/deployment.yaml  # kept for reference, not applied
    secrets/README.md
  Makefile                   # NEW: build/push/deploy targets
```

### Pattern 1: K8s Deployment Manifest
**What:** A Deployment resource for the real MCP server, replacing the nginx placeholder.
**When to use:** When transitioning from placeholder to real server.

Key details for the Deployment:
- **Image:** `ghcr.io/hellothisisflo/sketchpad:latest` (with ability to pin SHA)
- **Port:** containerPort 8000 (FastMCP's default)
- **Labels:** `app: sketchpad` (must match Service selector and existing cloudflared routing)
- **Volume mounts:** Two PVCs -- `sketchpad-data` at `/data` and `sketchpad-state` at `/state`
- **Environment variables:** From K8s Secrets (`github-oauth`, `encryption-key`) + ConfigMap or inline values
- **Health probe:** HTTP GET on a custom health endpoint or simply check that `/mcp` returns (even 401 is "alive")
- **Resource limits:** Conservative for a single-user personal server

```yaml
# Example Deployment structure
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sketchpad
  namespace: sketchpad
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sketchpad
  template:
    metadata:
      labels:
        app: sketchpad
    spec:
      containers:
        - name: sketchpad
          image: ghcr.io/hellothisisflo/sketchpad:latest
          ports:
            - containerPort: 8000
          env:
            - name: SERVER_URL
              value: "https://thehome-sketchpad.kempenich.dev"
            - name: DATA_DIR
              value: "/data"
            - name: STATE_DIR
              value: "/state"
            - name: GITHUB_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: github-oauth
                  key: client-id
            - name: GITHUB_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: github-oauth
                  key: client-secret
            - name: JWT_SIGNING_KEY
              valueFrom:
                secretKeyRef:
                  name: encryption-key
                  key: jwt-signing-key
            - name: STORAGE_ENCRYPTION_KEY
              valueFrom:
                secretKeyRef:
                  name: encryption-key
                  key: storage-encryption-key
          volumeMounts:
            - name: data
              mountPath: /data
            - name: state
              mountPath: /state
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /mcp
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
            # 401 is expected (no auth token), but proves the server is alive
            # FastMCP returns 401 for unauthenticated /mcp requests
          readinessProbe:
            httpGet:
              path: /mcp
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: sketchpad-data
        - name: state
          persistentVolumeClaim:
            claimName: sketchpad-state
```

**Important probe note:** FastMCP does not expose a dedicated `/health` endpoint by default. The `/mcp` endpoint returns 401 without a token, but HTTP probes consider any response (including 4xx) as failure unless you use a TCP or exec probe. Two options:
1. Use `tcpSocket` probe on port 8000 (simplest, proves server is listening)
2. Add a custom health route via FastMCP's `@mcp.custom_route("/health")` decorator
3. Use an exec probe: `exec: { command: ["python", "-c", "import httpx; httpx.get('http://localhost:8000/mcp')"] }` -- this succeeds as long as the server responds, regardless of HTTP status

**Recommendation:** Use a `tcpSocket` probe for liveness (simplest, most reliable) or add a `/health` custom route to the FastMCP server. The custom route is cleaner and can return `{"status": "ok"}` just like the placeholder did.

### Pattern 2: Service Update
**What:** The existing Service selects `app: sketchpad` pods on port 80 -> targetPort 80. The real server listens on 8000.
**Critical insight:** The Cloudflare Tunnel is configured to route to `http://sketchpad.sketchpad.svc.cluster.local:80`. Rather than changing the Tunnel config (manual dashboard step), update the Service to keep port 80 externally but map to targetPort 8000.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sketchpad
  namespace: sketchpad
spec:
  type: ClusterIP
  selector:
    app: sketchpad
  ports:
    - port: 80
      targetPort: 8000  # Changed from 80 to 8000
```

This way the Cloudflare Tunnel configuration stays unchanged -- it still routes to port 80 of the Service, which forwards to port 8000 of the pod.

### Pattern 3: Makefile Structure
**What:** Build/deploy workflow for container operations.

```makefile
# Key variables
IMAGE := ghcr.io/hellothisisflo/sketchpad
SHA   := $(shell git rev-parse --short HEAD)
TAG   := sha-$(SHA)

.PHONY: build push deploy all

build:
	docker build -t $(IMAGE):$(TAG) -t $(IMAGE):latest .

push:
	docker push $(IMAGE):$(TAG)
	docker push $(IMAGE):latest

deploy:
	kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
	kubectl rollout status deployment/sketchpad -n sketchpad --timeout=120s

all: build push deploy
```

**Note on CI interaction:** GitHub Actions CI already builds and pushes on every push to main. The Makefile provides a manual alternative for when the user wants to deploy without waiting for CI, or when iterating quickly. Both produce the same image tags (`sha-<hash>` + `latest`).

### Pattern 4: Claude Code Test Skill
**What:** A skill at `.claude/skills/test-sketchpad/SKILL.md` that provides a guided test walkthrough.
**How invoked:** `/test-sketchpad` in Claude Code CLI.

```yaml
---
name: test-sketchpad
description: Test the Sketchpad MCP server integration by walking through read, write, and read-back operations
disable-model-invocation: true
---

# Test Sketchpad Integration

Walk through each test step interactively, reporting what happens at each step.

## Steps

1. **Read current content**: Call the `read_file` tool. Report what you see.
2. **Write new content**: Call `write_file` with test content that includes a timestamp. Report the result.
3. **Read back**: Call `read_file` again. Verify the content matches what was written.
4. **Report**: Summarize: did all 3 steps succeed?
```

**Key design decisions:**
- `disable-model-invocation: true` -- only triggered explicitly by user typing `/test-sketchpad`
- Simple steps -- the skill should work with any MCP server configuration (local or remote)
- The skill tests the MCP tools themselves, not the OAuth flow (OAuth is handled by Claude Code's `/mcp` authentication)

### Anti-Patterns to Avoid
- **Changing Cloudflare Tunnel config when you can change the Service:** The tunnel routes to `sketchpad.sketchpad.svc.cluster.local:80`. Keep port 80 on the Service and remap targetPort to 8000. Avoids a manual dashboard step.
- **Deleting the placeholder before the real server is ready:** Apply the new Deployment first (it takes over the `app: sketchpad` label), then delete the placeholder. Or better: the new Deployment uses the same selector label, so K8s will route traffic to whichever pod is running.
- **Running `make push` without `make build` first:** The `all` target chains them, but document that `push` requires a recent `build`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth flow testing | Custom curl script | `test_oauth.py` (exists) | Already handles SSE, PKCE, DCR, token exchange -- 580+ lines of tested code |
| Container build CI | Manual docker push | GitHub Actions `build.yaml` | Already pushes `sha-<hash>` + `latest` on every push to main |
| MCP protocol handling | Raw HTTP calls | Claude Code CLI + FastMCP | Claude Code handles OAuth discovery, DCR, PKCE natively |
| K8s secret management | YAML with base64 values | `kubectl create secret` | Secrets already created in Phase 1, just reference them |

## Common Pitfalls

### Pitfall 1: GitHub OAuth App Callback URL Mismatch
**What goes wrong:** The OAuth flow fails because the GitHub OAuth App's callback URL doesn't match the server's production URL.
**Why it happens:** During Phase 2, the callback URL was changed to the local dev tunnel (`themac-sketchpad.kempenich.dev/auth/callback`). For production, it needs to point to `thehome-sketchpad.kempenich.dev/auth/callback`.
**How to avoid:** As a manual step during deployment, update the GitHub OAuth App callback URL to `https://thehome-sketchpad.kempenich.dev/auth/callback`. Note: the correct path is `/auth/callback` (FastMCP's default), NOT `/github/callback` (which was incorrectly documented in Phase 1's `docs/github-oauth-app.md`).
**Warning signs:** OAuth flow opens browser but returns error about redirect_uri mismatch.

### Pitfall 2: Callback URL Path Discrepancy in Docs
**What goes wrong:** The `docs/github-oauth-app.md` from Phase 1 says the callback path is `/github/callback`, but FastMCP actually uses `/auth/callback`.
**Why it happens:** Phase 1 docs were written before the server was built. Phase 2 research and local-development.md correctly document `/auth/callback`.
**How to avoid:** Fix the callback URL in `docs/02-github-oauth-app.md` during the doc consolidation. The correct URL is `https://thehome-sketchpad.kempenich.dev/auth/callback`.
**Warning signs:** Phase 1 doc says `/github/callback`, Phase 2 doc and server code say `/auth/callback`.

### Pitfall 3: Placeholder Service Port Conflict
**What goes wrong:** The new Deployment starts but isn't reachable because the placeholder's Service is still routing to port 80.
**Why it happens:** The placeholder `k8s/placeholder/deployment.yaml` bundles a ConfigMap, Deployment, AND Service in one file. The Service selects `app: sketchpad` on port 80 -> targetPort 80.
**How to avoid:** Create a separate `k8s/service.yaml` with port 80 -> targetPort 8000. Delete the placeholder Deployment (but the Service is the same name, so `kubectl apply` on the new service.yaml will update it in place). The placeholder Deployment name is `sketchpad-placeholder`, distinct from the new Deployment name `sketchpad`.
**Warning signs:** `kubectl get pods` shows both placeholder and real pods; traffic still hitting placeholder.

### Pitfall 4: OAuth State Not Persisting Across Pod Restarts
**What goes wrong:** After `kubectl rollout restart`, previously issued tokens are invalid and Claude must re-authenticate.
**Why it happens:** The FileTreeStore stores OAuth state (client registrations, tokens) on disk. If the volume mount is missing or points to a wrong path, state lives in the ephemeral container filesystem.
**How to avoid:** Verify STATE_DIR env var is `/state` and the PVC `sketchpad-state` is mounted at `/state`. After restart, tokens should still work.
**Warning signs:** Users must re-authenticate after every pod restart.

### Pitfall 5: Claude.ai Web Connector OAuth `about:blank` Bug
**What goes wrong:** Adding the server as a connector via claude.ai web interface fails with an `about:blank` loop.
**Why it happens:** Known bug (issue #11814, closed as duplicate). Claude Desktop and claude.ai web have a broken OAuth client implementation for custom MCP servers.
**How to avoid:** Use Claude Code CLI as the primary test client (it works). For phone testing, the connector added via claude.ai web *may* work (the bug status is unclear for connectors). If it fails, the workaround is to use Claude Code CLI on a phone or laptop as the test surface.
**Warning signs:** Browser opens to `about:blank` instead of GitHub OAuth page; zero requests hit the server.

### Pitfall 6: Liveness Probe Failing on 401
**What goes wrong:** Kubernetes keeps restarting the pod because the liveness probe gets 401 from `/mcp`.
**Why it happens:** HTTP probes consider any non-2xx response as failure. FastMCP returns 401 for unauthenticated requests to `/mcp`.
**How to avoid:** Use `tcpSocket` probe (checks port 8000 is listening) or add a custom `/health` route to the FastMCP server via `@mcp.custom_route`.
**Warning signs:** Pod shows `CrashLoopBackOff` or many restarts despite server actually running.

## Code Examples

### Adding the MCP Server to Claude Code CLI
```bash
# Source: https://code.claude.com/docs/en/mcp
# Add the server with HTTP transport (OAuth handled automatically)
claude mcp add --transport http sketchpad https://thehome-sketchpad.kempenich.dev/mcp

# Authenticate via OAuth (opens browser)
# Inside Claude Code:
> /mcp
# Select "Authenticate" for sketchpad, complete GitHub login in browser
```

**Key points:**
- The URL must include the `/mcp` path (the MCP endpoint)
- Claude Code handles OAuth discovery (fetches `/.well-known/oauth-authorization-server`), DCR, and PKCE automatically
- Authentication tokens are stored securely and refreshed automatically
- If browser redirect fails after auth, paste the callback URL from browser into the URL prompt in Claude Code

### Adding the Server as a Claude.ai Web Connector (for Phone Sync)
```
1. Go to https://claude.ai/settings/connectors
2. Click "Add custom connector"
3. Enter URL: https://thehome-sketchpad.kempenich.dev/mcp
4. Give it a name (e.g., "Sketchpad")
5. Complete OAuth flow in browser (GitHub login)
6. The connector syncs automatically to Claude mobile apps
```

**Important:** Claude.ai's OAuth callback URL is `https://claude.ai/api/mcp/auth_callback`. This is a different redirect_uri than Claude Code CLI uses. The server must support DCR (which FastMCP does) so Claude.ai can register itself as a client with this callback URL.

### Custom Health Route for FastMCP
```python
# Source: https://gofastmcp.com/deployment/http
# Add to server.py, after mcp = FastMCP(...)

from starlette.responses import JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok", "service": "sketchpad"})
```

### Makefile Pattern
```makefile
# Variables
IMAGE  := ghcr.io/hellothisisflo/sketchpad
SHA    := $(shell git rev-parse --short HEAD)
TAG    := sha-$(SHA)
NS     := sketchpad

.PHONY: build push deploy all status

build:
	docker build -t $(IMAGE):$(TAG) -t $(IMAGE):latest .

push:
	docker push $(IMAGE):$(TAG)
	docker push $(IMAGE):latest

deploy:
	kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n $(NS)
	kubectl rollout status deployment/sketchpad -n $(NS) --timeout=120s

all: build push deploy

status:
	kubectl get pods -n $(NS)
	kubectl get svc -n $(NS)
```

### Adapting test_oauth.py for Live URL
The existing `test_oauth.py` already reads `SERVER_URL` from `.env` and uses it for all requests. To test against the production server:

```bash
# Option 1: Temporarily update .env
# Set SERVER_URL=https://thehome-sketchpad.kempenich.dev in .env
uv run python test_oauth.py

# Option 2: Override via environment variable
SERVER_URL=https://thehome-sketchpad.kempenich.dev uv run python test_oauth.py
```

**Note:** The test script reads `.env` via `dotenv_values()`, but the env var approach (Option 2) would need a small code change since `dotenv_values()` reads the file, not the environment. The simpler approach is to update `.env` temporarily or add a CLI argument.

## State of the Art

| Old Approach (Placeholder) | Current Approach (Phase 3) | Impact |
|---------------------------|---------------------------|--------|
| nginx placeholder on port 80 | Real FastMCP server on port 8000 | Service targetPort changes from 80 to 8000 |
| Manual docker build/push | Makefile + GitHub Actions CI | Two paths: CI for every push, Makefile for manual/quick deploys |
| Flat docs/ with descriptive names | Numbered docs with README index | Sequential setup order is clear |
| No test harness | Claude Code `/test-sketchpad` skill | Repeatable integration testing |
| Local-only OAuth testing | test_oauth.py against live URL + Claude Code CLI | Full E2E from real client |

**Deprecated/outdated:**
- The `k8s/placeholder/deployment.yaml` should NOT be applied after Phase 3 deploys the real server. Keep the file for reference but document that it's superseded.

## Deployment Sequence (Critical)

The layer-by-layer verification approach maps to this sequence:

### Layer 1: K8s Deployment
1. Delete the placeholder deployment: `kubectl delete deployment sketchpad-placeholder -n sketchpad`
2. Delete the placeholder ConfigMap: `kubectl delete configmap placeholder-config -n sketchpad`
3. Apply new manifests: `kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml`
4. Wait for rollout: `kubectl rollout status deployment/sketchpad -n sketchpad`
5. **Verify:** `kubectl get pods -n sketchpad` shows `sketchpad-xxxxx` pod Running

### Layer 2: Tunnel Connectivity
1. **Verify:** `curl -sf https://thehome-sketchpad.kempenich.dev/.well-known/oauth-authorization-server` returns OAuth metadata JSON
2. If it fails: check Service port mapping, cloudflared logs, tunnel dashboard

### Layer 3: OAuth Flow
1. Update GitHub OAuth App callback URL to `https://thehome-sketchpad.kempenich.dev/auth/callback`
2. Update `.env` SERVER_URL to `https://thehome-sketchpad.kempenich.dev`
3. Run `uv run python test_oauth.py`
4. **Verify:** All checks pass (or expected SKIPs for refresh tokens with GitHub provider)

### Layer 4: Claude Code CLI
1. `claude mcp add --transport http sketchpad https://thehome-sketchpad.kempenich.dev/mcp`
2. In Claude Code: `/mcp` -> Authenticate -> GitHub login
3. Use `/test-sketchpad` skill to verify read/write/read-back
4. **Verify:** All three tool calls succeed

### Layer 5: Phone / Claude.ai
1. Go to claude.ai/settings/connectors -> Add custom connector -> URL: `https://thehome-sketchpad.kempenich.dev/mcp`
2. Complete OAuth in browser
3. Open Claude AI on phone, start new conversation
4. Ask Claude to read the sketchpad, write something, read it back
5. **Verify:** Content persists across conversations

### Layer 6: Persistence Test
1. `kubectl rollout restart deployment/sketchpad -n sketchpad`
2. Wait for new pod to be Running
3. In Claude, read the sketchpad -- should show content from previous session
4. **Verify:** Data survives pod restart

## Open Questions

1. **Health Check Endpoint Approach**
   - What we know: FastMCP supports `@mcp.custom_route` for custom HTTP endpoints. TCP socket probes work without any code changes. The placeholder used a JSON health response.
   - What's unclear: Whether adding a `/health` route is worth the code change vs. using a simpler `tcpSocket` probe.
   - Recommendation: Add a `/health` custom route for consistency with the placeholder and to enable `curl` health checks from outside the cluster. It's a 4-line code change.

2. **Claude.ai Web Connector Reliability**
   - What we know: Claude Code CLI OAuth works perfectly. Claude.ai web has a known `about:blank` bug (#11814) for some OAuth servers. The bug was closed as duplicate (possibly fixed?).
   - What's unclear: Whether the fix has been deployed. The issue was closed Nov 2025, and the project uses DCR which is supported.
   - Recommendation: Try it. If it fails, document as a known limitation and use Claude Code CLI as the verified test path. E2E-01 and E2E-02 can be satisfied via Claude Code CLI.

3. **test_oauth.py Parameterization**
   - What we know: The script reads SERVER_URL from `.env`. For production testing, `.env` needs to temporarily point to production URL.
   - What's unclear: Whether to add a CLI argument (`--url`) or just document the `.env` update approach.
   - Recommendation: Keep it simple -- document the `.env` update approach. Adding CLI args is Claude's discretion per CONTEXT.md.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | test_oauth.py (custom E2E script) + Claude Code skill |
| Config file | None (script reads .env) |
| Quick run command | `uv run python test_oauth.py` |
| Full suite command | `uv run python test_oauth.py` + manual Claude Code `/test-sketchpad` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| E2E-01 | Read sketchpad from Claude AI on phone | manual-only | N/A (phone interaction) | N/A |
| E2E-02 | Write to sketchpad from Claude AI on phone | manual-only | N/A (phone interaction) | N/A |
| E2E-03 | Data persists across conversations | manual + semi-auto | `kubectl rollout restart deployment/sketchpad -n sketchpad` then Claude read | N/A |
| DOCS-01 | docs/ folder with index and guides | smoke | `test -f docs/README.md && ls docs/0[1-5]-*.md \| wc -l` (expect 5) | N/A Wave 0 |
| DOCS-04 | Claude AI setup guide for phone | smoke | `test -f docs/05-claude-ai-setup.md && grep -q "phone" docs/05-claude-ai-setup.md` | N/A Wave 0 |

**Manual-only justification for E2E-01, E2E-02:** These require human interaction with Claude AI on a phone -- cannot be automated. The `/test-sketchpad` skill provides a semi-automated proxy when run from Claude Code CLI.

### Sampling Rate
- **Per task commit:** `kubectl get pods -n sketchpad` + `curl -sf https://thehome-sketchpad.kempenich.dev/.well-known/oauth-authorization-server`
- **Per wave merge:** `uv run python test_oauth.py` against live URL
- **Phase gate:** Full E2E from Claude Code CLI + phone test before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/README.md` -- docs index with Quick Start
- [ ] `docs/04-deploy.md` -- deployment guide
- [ ] `docs/05-claude-ai-setup.md` -- Claude AI setup guide
- [ ] `k8s/deployment.yaml` -- real MCP server Deployment
- [ ] `k8s/service.yaml` -- updated Service (targetPort 8000)
- [ ] `Makefile` -- build/push/deploy workflow
- [ ] `.claude/skills/test-sketchpad/SKILL.md` -- test skill
- [ ] Optionally: `/health` endpoint in `src/sketchpad/server.py`

## Sources

### Primary (HIGH confidence)
- [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) -- exact CLI commands for `claude mcp add`, OAuth authentication flow, `/mcp` command
- [Claude Code skills docs](https://code.claude.com/docs/en/skills) -- SKILL.md format, frontmatter, directory structure
- [FastMCP HTTP deployment](https://gofastmcp.com/deployment/http) -- `@mcp.custom_route` for health checks, stateless mode, production patterns
- Existing codebase: `k8s/`, `src/sketchpad/`, `Dockerfile`, `test_oauth.py`, `docs/` -- all read directly

### Secondary (MEDIUM confidence)
- [Claude Help Center - Custom connectors](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers) -- claude.ai web connector setup steps
- [Claude Help Center - Getting started with connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) -- Settings > Connectors > Add custom connector
- [DEV.to - Remote MCP on mobile](https://dev.to/zhizhiarv/how-to-set-up-remote-mcp-on-claude-iosandroid-mobile-apps-3ce3) -- mobile sync via web configuration
- [Kubernetes docs - rollout status](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_status/) -- `--timeout` flag for deploy waiting

### Tertiary (LOW confidence)
- [GitHub issue #11814](https://github.com/anthropics/claude-code/issues/11814) -- about:blank OAuth bug status (closed as duplicate, unclear if fixed)
- Claude.ai OAuth callback URL (`https://claude.ai/api/mcp/auth_callback`) -- mentioned in multiple sources but not officially documented by Anthropic

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist from Phases 1-2, no new dependencies
- Architecture: HIGH -- K8s Deployment patterns are standard; Claude Code CLI commands verified from official docs
- Pitfalls: HIGH -- callback URL discrepancy found by cross-referencing Phase 1 and Phase 2 docs; probe failure mode verified from K8s docs
- Claude.ai web connector: MEDIUM -- documented in help center, but about:blank bug adds uncertainty

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable stack, no fast-moving components)
