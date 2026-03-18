# Architecture Research

**Domain:** Remote MCP server with OAuth 2.1 — Python, Kubernetes, Cloudflare Tunnel
**Researched:** 2026-03-02
**Confidence:** HIGH (official MCP spec, official Cloudflare docs, FastMCP docs, verified against Python SDK source)

---

## Standard Architecture

### System Overview

```
Internet
    │
    ▼
┌──────────────────────────────────────────────┐
│  Cloudflare Edge (DNS + TLS termination)      │
│  mcp.yourdomain.com → Cloudflare Tunnel       │
└──────────────────────────┬───────────────────┘
                           │ encrypted outbound tunnel
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (Talos OS, home network / CGNAT)              │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │  Namespace: sketchpad                                     │     │
│  │                                                           │     │
│  │  ┌─────────────────────┐    ┌────────────────────────┐  │     │
│  │  │  Pod: mcp-server     │    │  Pod: cloudflared      │  │     │
│  │  │  ┌───────────────┐  │    │  (adjacent Deployment) │  │     │
│  │  │  │ FastMCP +     │  │    │  Routes tunnel traffic │  │     │
│  │  │  │ GitHubProvider│  │    │  to mcp-server Service │  │     │
│  │  │  │ uvicorn ASGI  │  │    └────────────┬───────────┘  │     │
│  │  │  │ :8000/mcp     │  │                 │               │     │
│  │  │  └───────┬───────┘  │                 │ HTTP          │     │
│  │  │          │ PVC mount │                 ▼               │     │
│  │  │  ┌───────▼───────┐  │    ┌────────────────────────┐  │     │
│  │  │  │ /data/        │  │◄───│  Service: mcp-server    │  │     │
│  │  │  │ sketchpad.txt │  │    │  ClusterIP :8000        │  │     │
│  │  │  └───────────────┘  │    └────────────────────────┘  │     │
│  │  └─────────────────────┘                                 │     │
│  │                                                           │     │
│  │  ┌──────────────────┐                                    │     │
│  │  │  PVC: sketchpad  │  (bound to StorageClass)           │     │
│  │  └──────────────────┘                                    │     │
│  └──────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘

External:
  GitHub OAuth API (api.github.com) ── called by GitHubProvider
  Claude AI (claude.ai)             ── the MCP client
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| FastMCP server | MCP protocol handler: tools, resource server logic | `FastMCP` + `@mcp.tool()` decorators |
| GitHubProvider (OAuth layer) | Acts as auth server to Claude, OAuth client to GitHub; issues JWT tokens | `fastmcp.server.auth.providers.github.GitHubProvider` |
| OAuth endpoints (auto-generated) | Serve `/.well-known/*`, `/register`, `/authorize`, `/token` | Mounted by FastMCP when `auth=` is set |
| Bearer token middleware | Validate JWT on every MCP request before tool dispatch | Built into FastMCP auth layer |
| Tool handlers | Read/write single file from PVC mount | Two `@mcp.tool()` functions |
| uvicorn | ASGI server, runs the FastMCP HTTP app | `mcp.http_app()` + uvicorn |
| cloudflared (adjacent Pod) | Outbound tunnel to Cloudflare edge; receives internet traffic | Official `cloudflare/cloudflared` image |
| ClusterIP Service | Internal DNS name for cloudflared → mcp-server routing | `mcp-server-service:8000` |
| PersistentVolumeClaim | Persistent file storage surviving pod restarts | Bound via StorageClass (local-path or Longhorn) |
| Secret: github-oauth | GitHub client_id + client_secret | K8s Secret, env vars injected |
| Secret: cloudflare-tunnel-token | Cloudflare tunnel token | K8s Secret, env var injected |

---

## Recommended Project Structure

```
sketchpad/
├── server/
│   ├── main.py              # FastMCP app, GitHubProvider setup, tool handlers
│   ├── tools/
│   │   └── sketchpad.py     # read_file() and write_file() tool implementations
│   └── requirements.txt     # fastmcp, uvicorn
├── k8s/
│   ├── namespace.yaml        # namespace: sketchpad
│   ├── secret-github.yaml    # GitHub client_id + client_secret (gitignored)
│   ├── secret-tunnel.yaml    # Cloudflare tunnel token (gitignored)
│   ├── pvc.yaml              # PVC for /data/sketchpad.txt
│   ├── deployment-mcp.yaml   # MCP server Deployment + volume mount
│   ├── service-mcp.yaml      # ClusterIP Service :8000
│   └── deployment-cloudflared.yaml  # cloudflared adjacent Deployment
├── .env.example              # GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, BASE_URL
└── .planning/
    └── research/
        └── ARCHITECTURE.md  # this file
```

### Structure Rationale

- **server/**: All Python source isolated from infra; can be developed and tested locally without K8s
- **k8s/**: All manifests in one place; apply with `kubectl apply -f k8s/` for a single namespace
- **secrets not committed**: `secret-*.yaml` files contain real credentials and must stay out of git
- **tools/ subfolder**: Even with two trivial tools, keeps `main.py` clean; easy to expand for vault project

---

## Architectural Patterns

### Pattern 1: OAuth Proxy (Third-Party Auth Delegation)

**What:** The MCP server acts as an OAuth 2.1 server to Claude (the MCP client) but delegates identity verification to GitHub as the upstream identity provider. The server issues its own JWT tokens to Claude after confirming the user authenticated with GitHub.

**When to use:** When you want a personal identity provider (GitHub) without running your own user database.

**Trade-offs:**
- Pro: No user management, GitHub handles credentials
- Pro: FastMCP's `GitHubProvider` abstracts the complexity
- Con: Two OAuth hops (Claude → Server, Server → GitHub)
- Con: Server must be reachable for the GitHub callback redirect

**Key code pattern:**

```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://mcp.yourdomain.com",  # public URL for OAuth callbacks
)

mcp = FastMCP("Sketchpad", auth=auth)

@mcp.tool()
def read_file() -> str:
    """Read the sketchpad file"""
    with open("/data/sketchpad.txt", "r") as f:
        return f.read()

@mcp.tool()
def write_file(content: str) -> str:
    """Write content to the sketchpad file"""
    with open("/data/sketchpad.txt", "w") as f:
        f.write(content)
    return "written"

app = mcp.http_app()  # ASGI app for uvicorn
```

### Pattern 2: Adjacent cloudflared Deployment (Not Sidecar)

**What:** cloudflared runs as a separate Deployment (not a sidecar container in the MCP pod). It routes traffic to the MCP server via Kubernetes internal DNS (`http://mcp-server-service:8000`).

**When to use:** Always for homelab/self-hosted setups. Sidecar would couple cloudflared restarts to app restarts.

**Trade-offs:**
- Pro: Independent scaling and restart of tunnel vs app
- Pro: One cloudflared instance can serve multiple services
- Con: Slightly more complex manifest structure (two Deployments)

**Key K8s pattern:**

```yaml
# deployment-cloudflared.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: sketchpad
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
        - name: cloudflared
          image: cloudflare/cloudflared:latest
          env:
            - name: TUNNEL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflare-tunnel-token
                  key: token
          command:
            - cloudflared
            - tunnel
            - --no-autoupdate
            - --metrics
            - 0.0.0.0:2000
            - run
          livenessProbe:
            httpGet:
              path: /ready
              port: 2000
            initialDelaySeconds: 10
            periodSeconds: 10
```

### Pattern 3: MCP Server as Resource Server Only (draft spec)

**What:** Per the MCP draft specification (2025), the MCP server's role is strictly as an OAuth 2.1 resource server — it validates tokens and serves tools. The OAuth endpoints (`/authorize`, `/token`, `/register`) are provided by the auth layer (FastMCP's GitHubProvider), not custom code.

**When to use:** Always. This is the current MCP spec pattern. Do not build custom auth endpoints.

**Trade-offs:**
- Pro: Correct per spec; Claude AI expects this structure
- Pro: FastMCP handles all endpoint routing automatically
- Con: Cannot skip auth layer for testing — must mock it

**What the MCP server exposes (via FastMCP auto-generation):**

| Endpoint | Purpose | Standard |
|----------|---------|---------|
| `/.well-known/oauth-protected-resource` | Points Claude to the auth server | RFC 9728 |
| `/.well-known/oauth-authorization-server` | Auth server metadata (when server is its own AS) | RFC 8414 |
| `POST /register` | Dynamic Client Registration | RFC 7591 |
| `GET /authorize` | Authorization endpoint — redirects to GitHub | OAuth 2.1 |
| `POST /token` | Token exchange (auth code → JWT) | OAuth 2.1 |
| `POST /mcp` | MCP JSON-RPC calls (protected by Bearer middleware) | MCP spec |
| `GET /mcp` | MCP SSE stream (protected by Bearer middleware) | MCP spec |

---

## Data Flow

### 1. Discovery + Registration Flow (first connection)

```
Claude AI
    │
    │ 1. POST /mcp (no token)
    ▼
MCP Server
    │ 2. HTTP 401 + WWW-Authenticate: Bearer resource_metadata=".../.well-known/oauth-protected-resource"
    ▼
Claude AI
    │ 3. GET /.well-known/oauth-protected-resource
    ▼
MCP Server → returns JSON: { authorization_servers: ["https://mcp.yourdomain.com"] }
    │
Claude AI
    │ 4. GET /.well-known/oauth-authorization-server
    ▼
MCP Server → returns metadata: { registration_endpoint, authorization_endpoint, token_endpoint, ... }
    │
Claude AI
    │ 5. POST /register  (Dynamic Client Registration)
    ▼
MCP Server (GitHubProvider) → stores client, returns { client_id, client_secret }
    │
    ▼  (Registration complete, proceed to auth flow)
```

### 2. Authorization Flow (login with GitHub)

```
Claude AI
    │ 6. Open browser to GET /authorize?client_id=...&code_challenge=...&resource=...
    ▼
MCP Server (GitHubProvider)
    │ 7. Redirect to GitHub /login/oauth/authorize
    ▼
GitHub
    │ 8. User logs in, authorizes
    │ 9. Redirect to https://mcp.yourdomain.com/callback?code=GITHUB_CODE
    ▼
MCP Server (GitHubProvider callback handler)
    │ 10. Exchange GITHUB_CODE → GitHub access token
    │ 11. Verify token with GitHub API (GET https://api.github.com/user)
    │ 12. Check user is in allowed list (single-user: just you)
    │ 13. Generate MCP-scoped JWT, store auth code mapping
    │ 14. Redirect to Claude's callback URL?code=MCP_AUTH_CODE
    ▼
Claude AI
    │ 15. POST /token  { code=MCP_AUTH_CODE, code_verifier=... }
    ▼
MCP Server (GitHubProvider)
    │ 16. Verify PKCE code_verifier against stored challenge
    │ 17. Return { access_token: JWT, refresh_token: ... }
    ▼
Claude AI (holds JWT)
```

### 3. Tool Call Flow (steady state)

```
Claude AI
    │ POST /mcp  Authorization: Bearer <JWT>
    │ Body: { method: "tools/call", params: { name: "read_file" } }
    ▼
Bearer middleware (FastMCP)
    │ Validate JWT signature + expiry + audience
    ▼
Tool handler: read_file()
    │ open("/data/sketchpad.txt")
    ▼
PersistentVolume (K8s PVC)
    │ file contents
    ▼
FastMCP response: { result: "file contents..." }
    ▼
Claude AI
```

### 4. Kubernetes Traffic Flow

```
Claude AI (phone)
    │ HTTPS mcp.yourdomain.com/mcp
    ▼
Cloudflare Edge (TLS termination, DNS)
    │ Cloudflare Tunnel (outbound from cluster)
    ▼
cloudflared Pod (namespace: sketchpad)
    │ HTTP http://mcp-server-service:8000
    ▼
ClusterIP Service (mcp-server-service)
    │ routes to Pod selector app=mcp-server
    ▼
MCP Server Pod (port 8000)
    │ /data/sketchpad.txt via PVC mount
    ▼
PersistentVolume
```

---

## Kubernetes Manifests Structure

### PVC

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: sketchpad-pvc
  namespace: sketchpad
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Mi
  storageClassName: local-path   # adjust to match cluster StorageClass
```

### MCP Server Deployment

```yaml
# deployment-mcp.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: sketchpad
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
        - name: mcp-server
          image: your-registry/sketchpad-mcp:latest
          ports:
            - containerPort: 8000
          env:
            - name: GITHUB_CLIENT_ID
              valueFrom:
                secretKeyRef:
                  name: github-oauth
                  key: client_id
            - name: GITHUB_CLIENT_SECRET
              valueFrom:
                secretKeyRef:
                  name: github-oauth
                  key: client_secret
            - name: BASE_URL
              value: "https://mcp.yourdomain.com"
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: sketchpad-pvc
```

### ClusterIP Service

```yaml
# service-mcp.yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
  namespace: sketchpad
spec:
  selector:
    app: mcp-server
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
```

### Cloudflare Tunnel Secret + Deployment

```yaml
# secret-tunnel.yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-tunnel-token
  namespace: sketchpad
stringData:
  token: <YOUR_CLOUDFLARE_TUNNEL_TOKEN>
---
# deployment-cloudflared.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudflared
  namespace: sketchpad
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudflared
  template:
    metadata:
      labels:
        app: cloudflared
    spec:
      containers:
        - name: cloudflared
          image: cloudflare/cloudflared:latest
          env:
            - name: TUNNEL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflare-tunnel-token
                  key: token
          command:
            - cloudflared
            - tunnel
            - --no-autoupdate
            - --metrics
            - 0.0.0.0:2000
            - run
          livenessProbe:
            httpGet:
              path: /ready
              port: 2000
            initialDelaySeconds: 10
            periodSeconds: 10
```

Cloudflare dashboard tunnel configuration: public hostname `mcp.yourdomain.com` → service `http://mcp-server-service.sketchpad.svc.cluster.local:8000`

---

## Anti-Patterns

### Anti-Pattern 1: Building Custom OAuth Endpoints

**What people do:** Implement `/authorize`, `/token`, `/register` from scratch in Python.

**Why it's wrong:** FastMCP's `GitHubProvider` does this correctly in ~3 lines of config. Rolling custom auth introduces PKCE bugs, incorrect WWW-Authenticate headers, and spec compliance failures that will silently break Claude AI's auth flow.

**Do this instead:** Use `FastMCP(..., auth=GitHubProvider(...))`. The endpoints are auto-mounted.

### Anti-Pattern 2: Cloudflare Tunnel as Sidecar

**What people do:** Add cloudflared as a second container in the same Pod as the MCP server.

**Why it's wrong:** Couples tunnel restarts to app restarts. Can't scale or update them independently. The MCP server loses its connection during any cloudflared update.

**Do this instead:** Two separate Deployments. cloudflared routes to the MCP server via the ClusterIP Service DNS name.

### Anti-Pattern 3: HostPath Storage

**What people do:** Use `hostPath` volume mounts to skip PVC complexity.

**Why it's wrong:** If the pod reschedules to a different node (even on a single-node homelab after a node rebuild), the data is gone. HostPath also requires knowing the specific node.

**Do this instead:** PVC backed by a StorageClass (local-path-provisioner or Longhorn). Talos ships without a default StorageClass — check/install one before deploying.

### Anti-Pattern 4: Exposing the MCP Server Port Directly

**What people do:** Open port 8000 on the node via NodePort or LoadBalancer service.

**Why it's wrong:** Behind CGNAT there are no inbound ports. Also removes Cloudflare's TLS termination and DDoS protection.

**Do this instead:** ClusterIP (internal only) for the MCP service. Cloudflare Tunnel as the sole internet ingress path.

### Anti-Pattern 5: Treating the 2025-03-26 Spec as Current

**What people do:** Follow examples based on the 2025-03-26 MCP authorization spec.

**Why it's wrong:** The current draft spec (2025) changed the architecture: the MCP server is now strictly a Resource Server. The new primary discovery mechanism is Protected Resource Metadata (RFC 9728) via WWW-Authenticate headers, not direct auth server metadata at the MCP server root. Dynamic Client Registration (RFC 7591) has been demoted to optional/legacy in favor of Client ID Metadata Documents.

**Do this instead:** Use FastMCP's GitHubProvider which tracks spec changes. Verify against `modelcontextprotocol.io/specification/draft/basic/authorization` before implementing any custom auth logic.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GitHub OAuth API | GitHubProvider calls `api.github.com/user` to verify opaque tokens | GitHub tokens are not JWTs; must call API to validate |
| Cloudflare Tunnel | cloudflared Pod holds outbound persistent connection to Cloudflare edge | Token stored in K8s Secret; configure hostname routing in Cloudflare dashboard |
| Claude AI (client) | Acts as OAuth 2.1 public client with PKCE; calls all standard endpoints | Claude requires DCR, PKCE, and Protected Resource Metadata |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| cloudflared → mcp-server | HTTP over ClusterIP Service DNS | No auth between these; auth is enforced by MCP server |
| FastMCP auth layer → tool handlers | Internal Python function call after Bearer token validated | `get_access_token()` context var available in tools if user identity needed |
| MCP server pod → PVC | POSIX file I/O at `/data/sketchpad.txt` | ReadWriteOnce; single pod only |

---

## Build Order (Component Dependencies)

The components have strict dependencies that determine phase/task ordering:

```
StorageClass (exists or install)
    └──► PVC (requires StorageClass)
             └──► MCP Server Pod (requires PVC)

GitHub OAuth App (register at github.com)
    └──► GitHub Secret (requires client_id + client_secret)
             └──► MCP Server Pod (requires env vars)

Cloudflare Tunnel (create in dashboard)
    └──► Tunnel Token Secret (requires token)
             └──► cloudflared Deployment (requires Secret)
                       └──► Cloudflare hostname routing (configure after cloudflared is running)

MCP Server code (FastMCP + GitHubProvider)
    └──► Container image (build from code)
             └──► MCP Server Pod (requires image + PVC + Secret)

MCP Server Pod + Service + Cloudflare hostname routing
    └──► End-to-end OAuth test from Claude AI
```

**Recommended build sequence:**

1. Register GitHub OAuth App → get client_id + client_secret
2. Verify/install StorageClass on Talos cluster
3. Create K8s namespace + Secrets (GitHub + tunnel token)
4. Write FastMCP server code + tools (testable locally with `mcp.run()`)
5. Build and push container image
6. Apply PVC + MCP server Deployment + Service
7. Apply cloudflared Deployment
8. Configure Cloudflare dashboard: hostname `mcp.yourdomain.com` → `http://mcp-server-service.sketchpad:8000`
9. Test OAuth flow end-to-end from Claude AI

---

## Scaling Considerations

This is a single-user personal tool. Scaling is not a concern.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (current) | Single replica, ReadWriteOnce PVC, no session affinity needed |
| Multi-user (future) | Switch `stateless_http=True`, ReadWriteMany PVC or per-user paths, token storage backend (Redis/DB) |

The main first bottleneck for a personal tool is not performance but auth state storage: FastMCP's default in-memory storage for OAuth client registrations and tokens will be lost on pod restarts. For a single-user tool this is acceptable (user re-authenticates once after restart). For any multi-user or production use, add a persistent storage backend.

---

## Sources

- [MCP Authorization Specification (2025-03-26)](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization) — HIGH confidence, official spec
- [MCP Authorization Specification (draft)](https://modelcontextprotocol.io/specification/draft/basic/authorization) — HIGH confidence, current draft showing RFC 9728 as mandatory
- [FastMCP OAuth Proxy docs](https://gofastmcp.com/servers/auth/oauth-proxy.md) — HIGH confidence, official FastMCP docs
- [FastMCP HTTP deployment](https://gofastmcp.com/deployment/http.md) — HIGH confidence, official FastMCP docs
- [FastMCP GitHub provider](https://gofastmcp.com/python-sdk/fastmcp-server-auth-providers-github.md) — HIGH confidence, official FastMCP docs
- [Cloudflare Tunnel Kubernetes deployment guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/deployment-guides/kubernetes/) — HIGH confidence, official Cloudflare docs
- [MCP Python SDK auth module source](https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/auth/provider.py) — HIGH confidence, official SDK
- [MCP OAuth Gateway (atrawog) — architecture reference](https://github.com/atrawog/mcp-oauth-gateway) — MEDIUM confidence, community project showing validated patterns
- [Azure remote MCP Python OAuth sample](https://github.com/Azure-Samples/remote-mcp-webapp-python-auth-oauth) — MEDIUM confidence, reference implementation showing endpoint structure
- [Talos local storage docs](https://www.talos.dev/v1.10/kubernetes-guides/configuration/local-storage/) — HIGH confidence, official Talos docs

---

*Architecture research for: Remote MCP server with OAuth 2.1, Python, Kubernetes, Cloudflare Tunnel*
*Researched: 2026-03-02*
