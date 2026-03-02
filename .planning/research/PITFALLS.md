# Pitfalls Research

**Domain:** Remote MCP server with OAuth 2.1 (DCR + PKCE), Python, Kubernetes/Talos OS, Cloudflare Tunnel
**Researched:** 2026-03-02
**Confidence:** HIGH (majority of pitfalls confirmed by official docs, official GitHub issues, or multiple sources)

---

## Critical Pitfalls

These will cause a full restart of your OAuth implementation if you hit them.

---

### Pitfall 1: GitHub Does Not Support DCR — You Must Build Your Own Authorization Server

**What goes wrong:**

The user plans to use GitHub as the "identity provider." The natural beginner assumption is: point the OAuth layer at GitHub, done. But GitHub OAuth Apps do not implement Dynamic Client Registration (RFC 7591). Claude.ai requires DCR to automatically register itself. If there is no `/register` endpoint, Claude either falls back to a broken state, or reports "Incompatible auth server: does not support dynamic client registration" and refuses to connect.

There is a GitHub issue on the official `github/github-mcp-server` repo titled "Dynamic Client Registration not supported" where users hit exactly this on VS Code and Claude.

**Why it happens:**

"GitHub as identity provider" sounds like GitHub is your authorization server. It isn't. GitHub is an upstream identity provider (it can tell you who the user is). The authorization server — the thing that issues tokens to Claude — needs to be your own code or a dedicated OAuth server (Authlib, Dex, Ory Hydra, etc.) that wraps GitHub for login but speaks DCR to Claude.

**How to avoid:**

Treat GitHub OAuth as a login mechanism only (the user clicks "Sign in with GitHub" in the browser). Your Python server runs its own authorization server (using Authlib's `AuthorizationServer` or FastAPI with Authlib). That server exposes:
- `/.well-known/oauth-authorization-server` (RFC 8414 metadata)
- `/.well-known/oauth-protected-resource` (RFC 9728 metadata)
- `/oauth/register` (DCR endpoint, RFC 7591)
- `/oauth/authorize` (redirects to GitHub, returns auth code)
- `/oauth/token` (exchanges code for access token)

The DCR endpoint returns a `client_id` to Claude. GitHub is only involved in the user-facing browser login step.

**Warning signs:**

- Claude reports "does not support dynamic client registration" in connection logs
- Your authorization server metadata JSON has no `registration_endpoint` field
- You are trying to use `https://github.com/login/oauth/authorize` directly as your `authorization_endpoint` in the metadata you serve to Claude

**Phase to address:** OAuth Authorization Server implementation phase (early, before any Claude integration testing)

---

### Pitfall 2: The `about:blank` Loop — Claude.ai Web Sometimes Fails Even With a Correct Server

**What goes wrong:**

Your server is fully spec-compliant. MCP Inspector connects fine. Claude Code CLI connects fine. But when you add the server in Claude.ai web, Claude opens a browser window to `about:blank` and nothing happens. The server logs show zero inbound requests — Claude never even contacted the server.

This is a documented bug in Claude's OAuth proxy/client implementation (GitHub issue #11814 in `anthropics/claude-code`, marked as duplicate, not fixed as of early 2026).

**Why it happens:**

Claude.ai web uses an internal OAuth proxy that has different behavior from Claude Code CLI. The proxy has URL construction or validation logic that silently fails on certain server configurations without surfacing any error to the user.

**How to avoid:**

Build the server and test it with Claude Code CLI (`claude mcp add --transport http server-name https://yourserver.com`) first. Do not assume Claude.ai web will "just work" if CLI works — there may be additional compatibility requirements. When debugging, use: (1) MCP Inspector, (2) Claude Code CLI, (3) Claude.ai web, in that order. If CLI works but web fails, this is likely a Claude-side issue, not your server.

**Warning signs:**

- Claude.ai web shows a blank or empty browser popup
- Server access logs show zero requests during connection attempt
- MCP Inspector and Claude Code CLI both work correctly

**Phase to address:** Integration testing phase — set explicit success criteria as "works in Claude Code CLI" before attempting Claude.ai web.

---

### Pitfall 3: Wrong `WWW-Authenticate` Header Format Breaks Discovery

**What goes wrong:**

The MCP spec (2025-06-18) requires your MCP server to respond to unauthenticated requests with HTTP 401 and a specific `WWW-Authenticate` header format. The header must point to your Protected Resource Metadata URL (RFC 9728). If the format is wrong — wrong parameter name, missing quotes, wrong URL — the entire auth discovery chain breaks. Claude cannot find the authorization server and the flow never starts.

**Why it happens:**

There are two different things that look similar:
- The old approach pointed directly at the authorization server metadata URL
- The new 2025-06-18 spec requires pointing at the **resource server** metadata URL (RFC 9728), which then references the authorization server

Many tutorials and examples still show the old format or mix them up.

**How to avoid:**

The correct format is exactly:
```
WWW-Authenticate: Bearer resource_metadata="https://your-server.com/.well-known/oauth-protected-resource"
```

The key: `resource_metadata` (not `realm`, not `as_uri`, not `authorization_server`). The value must point to YOUR server's `/.well-known/oauth-protected-resource` endpoint, not to GitHub or any external auth server.

Your `/.well-known/oauth-protected-resource` response must then contain `"authorization_servers": ["https://your-server.com"]` pointing to your own auth layer.

**Warning signs:**

- OAuth flow never starts (no browser popup)
- Curl of your MCP endpoint returns 401 but the header looks like `WWW-Authenticate: Bearer realm="mcp"` without `resource_metadata`
- MCP Inspector reports it cannot find authorization server

**Phase to address:** OAuth server implementation phase.

---

### Pitfall 4: DCR `grant_types` Validation Bug in Python MCP Libraries

**What goes wrong:**

The Python MCP SDK's built-in DCR handler (as of mid-2025) rejects registration requests that include only `authorization_code` as the grant type. It requires BOTH `authorization_code` AND `refresh_token`, but RFC 7591 makes `refresh_token` optional. This causes HTTP 400 errors during Claude's registration attempt.

Separately, the FastMCP library has a similar validation bug (GitHub issue #2460) that was reported but may or may not be fixed in current versions.

**Why it happens:**

Library implementers added stricter-than-spec validation. Claude sends `"grant_types": ["authorization_code"]` during DCR. The library rejects it.

**How to avoid:**

Before starting: check the current version of your chosen MCP library (Python SDK or FastMCP) against the issue tracker. Test DCR registration manually with curl before trying Claude:

```bash
curl -X POST https://your-server.com/oauth/register \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris": ["https://claude.ai/api/mcp/auth_callback"], "grant_types": ["authorization_code"]}'
```

If you get a 400, you hit the bug. If using the Python MCP SDK, consider using Authlib's DCR implementation directly instead of the built-in one — it is more RFC-compliant.

**Warning signs:**

- DCR returns HTTP 400 with message like "grant_types must be authorization_code and refresh_token"
- Claude reports registration failure but server is reachable

**Phase to address:** OAuth server implementation phase — verify during initial DCR endpoint build.

---

### Pitfall 5: Python SDK RFC 9728 URL Path Bug With Non-Root MCP Paths

**What goes wrong:**

When the MCP server is served at a path (e.g., `https://your-server.com/mcp` instead of `https://your-server.com`), the Python MCP SDK constructs the protected resource metadata URL incorrectly. It serves the metadata at `/.well-known/oauth-protected-resource` (root) but advertises `/.well-known/oauth-protected-resource/mcp` (with path), or vice versa. Claude cannot find the metadata.

**Why it happens:**

Open bug in the Python SDK (GitHub issue #1052, filed June 2025, not confirmed fixed as of this writing). The RFC 9728 path-aware URL construction was not implemented.

**How to avoid:**

Serve your MCP endpoint at the root path: `https://your-server.com/mcp` → avoid. Use `https://your-server.com` or configure `settings.auth.resource_server_url` to match exactly. Test by manually curling both `/.well-known/oauth-protected-resource` and `<path>/.well-known/oauth-protected-resource` to see which one actually returns JSON.

**Warning signs:**

- Curl of `/.well-known/oauth-protected-resource` returns 404 or wrong content
- MCP Inspector or Claude cannot find authorization server metadata

**Phase to address:** OAuth server implementation phase — verify discovery endpoints before testing Claude integration.

---

### Pitfall 6: `redirect_uri` Mismatch — Claude's Callback URL vs What You Registered

**What goes wrong:**

Claude.ai uses `https://claude.ai/api/mcp/auth_callback` as its OAuth callback. But there is documentation that this may change to `https://claude.com/api/mcp/auth_callback`. If your authorization server validates redirect URIs exactly (which it must, for security), and Claude sends the one you did not register, the token exchange fails with `redirect_uri mismatch`.

There is also a reported bug (GitHub issue #10439) where Claude Code CLI sends a malformed `redirect_uri` with an unencoded space.

**Why it happens:**

The MCP spec and Claude's implementation are both in active development. The callback URL has changed and may change again. The DCR endpoint receives Claude's redirect_uri at registration time, so it should be registered dynamically — but only if your DCR implementation stores and validates the registered URIs per-client.

**How to avoid:**

Your DCR endpoint must store the `redirect_uris` array from the registration request and use that stored value during the authorization code exchange validation — not a hardcoded list. If Claude registers `https://claude.ai/api/mcp/auth_callback`, that is what gets stored. Do not hardcode callback URLs in your authorization server.

As a belt-and-suspenders measure, allowlist both `https://claude.ai/api/mcp/auth_callback` AND `https://claude.com/api/mcp/auth_callback` in any static configuration you have.

**Warning signs:**

- Token exchange returns error like `redirect_uri_mismatch` or `redirect_uri not registered for client`
- Claude completes the browser login but never receives a token
- Authorization server logs show the registered URI differs from the requested URI

**Phase to address:** OAuth server implementation phase.

---

### Pitfall 7: Talos OS Has No Default StorageClass — PVCs Pend Forever

**What goes wrong:**

You create a Kubernetes `PersistentVolumeClaim` manifest and apply it. The PVC stays in `Pending` state permanently. The pod that needs it never starts. Talos OS does not ship with any default StorageClass or storage provisioner — unlike managed K8s (GKE, EKS) or k3s, which include one.

**Why it happens:**

Beginners assume Kubernetes includes dynamic storage provisioning. It does not unless a CSI driver or provisioner is installed. On Talos, nothing is pre-installed.

**How to avoid:**

Install `local-path-provisioner` (Rancher's) before creating any PVCs. The Talos-specific setup requires:

1. A user volume configured in the Talos machine config at `/var/mnt/local-path-provisioner` (not the default `/opt/local-path-provisioner`, which is read-only on Talos's immutable filesystem)
2. A kustomization patch to set the provisioner's data path to match the mounted volume
3. Optionally mark it as the default StorageClass

Verify before creating the app PVC:
```bash
kubectl get storageclass
kubectl get pvc -A
```

**Warning signs:**

- `kubectl describe pvc <name>` shows `Events: no events` or `FailedBinding`
- `kubectl get pvc` shows `STATUS: Pending` indefinitely
- `kubectl get storageclass` returns `No resources found`

**Phase to address:** Kubernetes infrastructure setup phase (before deploying any app manifests).

---

## Moderate Pitfalls

---

### Pitfall 8: Cloudflare Tunnel TLS Double-Encryption Confusion

**What goes wrong:**

Cloudflare Tunnel terminates TLS externally and forwards traffic to your K8s service internally. Beginners sometimes configure the internal service to also expect HTTPS, causing TLS handshake failures. Or they set Cloudflare SSL mode to "Flexible" (only encrypts client→Cloudflare, not Cloudflare→origin), which sends HTTP to your server while your server expects HTTPS tokens.

**How to avoid:**

Set Cloudflare SSL/TLS mode to "Full" (encrypts end-to-end). Configure the internal cloudflared service to point to the K8s service using `http://` (not `https://`) since traffic inside the cluster is on a private network. OAuth requires HTTPS — but that HTTPS is provided by Cloudflare to the outside world; inside your cluster, HTTP is fine for the tunnel-to-service leg.

**Warning signs:**

- Browser sees SSL errors or mixed content warnings
- OAuth redirect fails with "redirect URI must use HTTPS" errors even though the public URL uses HTTPS
- Server receives double-encoded TLS or connection resets

**Phase to address:** Cloudflare Tunnel + Kubernetes networking phase.

---

### Pitfall 9: Cloudflare Tunnel Parameter Order Crashes cloudflared Pod

**What goes wrong:**

The `cloudflared` command in a Kubernetes deployment spec has strict parameter ordering. If parameters appear in the wrong order, `cloudflared` pods restart in a crash loop. The Cloudflare documentation explicitly warns about this but it is easy to miss.

**How to avoid:**

Follow the exact parameter order from the official Kubernetes deployment guide. The correct order is:
```
cloudflared tunnel --config /etc/cloudflared/config.yaml run
```
not
```
cloudflared tunnel run --config /etc/cloudflared/config.yaml
```

Do not use `autoscaling` for cloudflared — it does not load-balance across replicas. Replicas are for high availability only.

**Warning signs:**

- `kubectl get pods` shows cloudflared pods in `CrashLoopBackOff`
- `kubectl logs` for the pod shows argument parsing errors

**Phase to address:** Cloudflare Tunnel deployment phase.

---

### Pitfall 10: Port 443 Requirement for Claude.ai Web

**What goes wrong:**

Claude Desktop and Claude.ai web only connect to MCP servers on standard HTTPS port 443. If your server is exposed on a custom port (e.g., 8443), Claude.ai web will refuse to connect. Claude Code CLI is more permissive.

**How to avoid:**

Configure Cloudflare Tunnel to serve your MCP server on the standard public domain without a port suffix. Cloudflare handles the 443→internal routing. Your internal service can use any port; the public URL should not include a port number.

**Warning signs:**

- Claude.ai web refuses to add the server URL
- Works fine with Claude Code CLI (which accepts non-standard ports)

**Phase to address:** Cloudflare Tunnel configuration phase.

---

### Pitfall 11: Kubernetes Secrets Are Not Encrypted — Base64 Is Not Security

**What goes wrong:**

You store your GitHub OAuth client secret, session keys, or other credentials in Kubernetes Secrets. But by default, K8s Secrets are stored as base64-encoded plaintext in etcd and are trivially decodable. Anyone with `kubectl` access can read them. On a home cluster this may be low risk, but it sets a bad habit and can create real exposure if the kubeconfig is compromised.

**How to avoid:**

For this personal spike project, Kubernetes Secrets are acceptable, but understand what they are: base64 encoding, not encryption. Use `stringData:` fields in manifests so values do not need manual base64 encoding. Do not commit Secret manifests containing real credentials to git. If the cluster hosts other workloads, consider enabling encryption at rest in the kube-apiserver.

**Warning signs:**

- You have a `.yaml` file in your repo with `kind: Secret` and real credential values

**Phase to address:** Kubernetes secrets configuration phase.

---

### Pitfall 12: SSE Transport Deprecated — Use Streamable HTTP

**What goes wrong:**

The old MCP HTTP transport (HTTP + SSE, from spec 2024-11-05) is deprecated. The current spec (2025-06-18) uses Streamable HTTP. If you build on the old transport, you may work with some clients (old Claude Desktop versions) but fail with newer ones, or need to maintain both endpoints.

**How to avoid:**

Use the Streamable HTTP transport from the start. In the Python MCP SDK, this means using `mcp.server.fastmcp.FastMCP` with `transport="streamable-http"` (or the equivalent in the current SDK API). Check the Python SDK changelog for the exact parameter names as they changed between SDK versions.

**Warning signs:**

- Examples or tutorials showing `/sse` endpoint for the MCP connection URL
- Server using `StreamingResponse` with `text/event-stream` as the primary transport

**Phase to address:** MCP server implementation phase.

---

## Minor Pitfalls

---

### Pitfall 13: MCP Inspector "Works" Does Not Mean Claude "Works"

**What goes wrong:**

MCP Inspector is a useful debugging tool but has different OAuth behavior than Claude. Inspector successfully completes OAuth flows that Claude rejects, or manages credentials differently. "Works in Inspector" is a necessary but not sufficient condition for "works in Claude."

**How to avoid:**

Test in this order: curl (raw endpoint verification) → MCP Inspector (basic OAuth flow) → Claude Code CLI → Claude.ai web. Each client tests a different layer. Do not declare the OAuth flow "done" until it works in Claude Code CLI at minimum.

**Phase to address:** Integration testing phase.

---

### Pitfall 14: Talos OS Debugging — No SSH, No Shell

**What goes wrong:**

On a traditional Linux K8s node, you SSH into the node to inspect logs, check processes, or debug networking. On Talos OS, there is no SSH, no shell, and no package manager. Beginners waste time trying to SSH in or `kubectl exec` into system pods.

**How to avoid:**

Use `talosctl` for node-level operations: `talosctl logs`, `talosctl dmesg`, `talosctl service`. Use `kubectl logs` for pod logs. Use `kubectl describe pod` for event-level diagnosis. For network debugging within the cluster, deploy a temporary `netshoot` debug pod with `kubectl run -it --rm debug --image=nicolaka/netshoot`.

**Warning signs:**

- You are trying to SSH into nodes
- You are getting "connection refused" when trying to connect to nodes on port 22

**Phase to address:** All Kubernetes phases — operational mindset to establish early.

---

### Pitfall 15: OAuth Token Not Validated for Audience on the MCP Server

**What goes wrong:**

The MCP server accepts any valid JWT from your authorization server without checking the `aud` (audience) claim. A token issued for a different service (e.g., for a future Obsidian vault server) would be accepted. This creates a security boundary failure.

**How to avoid:**

Your token validation logic must check that the token's `aud` claim matches the canonical URI of this specific MCP server (e.g., `https://sketchpad.yourdomain.com`). The MCP spec mandates this. In Python with Authlib: verify the `aud` claim during JWT decoding. If using opaque tokens, store the intended audience at issuance and verify at validation time.

**Warning signs:**

- Token validation only checks signature and expiry, not audience
- The same token successfully authorizes requests to multiple different services

**Phase to address:** OAuth token validation implementation phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode `redirect_uri` allowlist instead of using DCR-stored URIs | Simpler code | Breaks when Claude's callback URL changes | Never — DCR must store per-client URIs |
| Skip audience validation in token verification | Faster to implement | Token from one service works on another | Never for OAuth |
| Use `hostPath` instead of PVC for persistence | No StorageClass needed | Data tied to a specific node; pod unschedulable if moved | Never in K8s |
| Combine authorization server and resource server in one codebase | Fewer services to deploy | Harder to reason about, audit, and evolve | Acceptable for this spike |
| Skip refresh token support | Simpler auth server | Users must re-authenticate when token expires (Claude re-auth is awkward) | Acceptable for initial MVP, add refresh tokens in v2 |
| Use `kubectl port-forward` instead of Cloudflare Tunnel for initial testing | Faster to test locally | Not publicly accessible; can't test real Claude.ai integration | Acceptable for local OAuth server testing only |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub OAuth | Treating GitHub as the authorization server that speaks to Claude | GitHub handles only user login (browser redirect); your own auth server speaks DCR to Claude |
| Claude.ai callback | Hardcoding only `claude.ai/api/mcp/auth_callback` | Register dynamically via DCR; also allowlist `claude.com/api/mcp/auth_callback` as fallback |
| Cloudflare Tunnel | Pointing tunnel at `https://` internal service | Point at `http://` internal K8s service; Cloudflare provides external HTTPS |
| Python MCP SDK | Using built-in auth helpers without verifying RFC compliance | Check GitHub issues for current DCR/RFC9728 bugs before writing auth code |
| Talos local-path-provisioner | Using default path `/opt/local-path-provisioner` | Must use `/var/mnt/local-path-provisioner` on Talos's writable volume |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Accepting tokens not issued for this resource (no audience validation) | Token from another service authenticates here | Validate `aud` claim on every request |
| Open DCR endpoint with no rate limiting | Registration DoS; storage exhaustion | Acceptable for personal single-user server; add rate limiting if multi-user |
| Logging full access tokens in server logs | Token theft from logs | Log only token prefixes/hashes for debugging; never full token values |
| Committing Kubernetes Secret manifests with real credentials to git | Credential exposure | Use `.gitignore` for secret manifests; use `stringData` not `data` |
| Storing GitHub OAuth app client secret in ConfigMap instead of Secret | Visible to all K8s users | Always use `kind: Secret` for credential values |

---

## "Looks Done But Isn't" Checklist

- [ ] **DCR endpoint:** Returns correct JSON including `client_id`, `redirect_uris`, `grant_types` — verify with curl, not just "no error"
- [ ] **RFC 9728 metadata:** `/.well-known/oauth-protected-resource` returns JSON with `authorization_servers` array — curl it manually
- [ ] **RFC 8414 metadata:** `/.well-known/oauth-authorization-server` returns JSON with `registration_endpoint`, `code_challenge_methods_supported: ["S256"]`, `token_endpoint_auth_methods_supported: ["none"]` — curl it manually
- [ ] **WWW-Authenticate header:** 401 response from MCP endpoint includes `Bearer resource_metadata="https://..."` — curl the `/mcp` endpoint without a token
- [ ] **PVC is Bound:** `kubectl get pvc` shows `STATUS: Bound`, not `Pending` — check before deploying app
- [ ] **StorageClass exists:** `kubectl get storageclass` shows at least one StorageClass — check before creating PVC
- [ ] **PKCE `code_challenge_method`:** Authorization server only accepts `S256`, never `plain` — verify in auth server config
- [ ] **Token audience binding:** Decoded JWT `aud` claim matches your server's canonical URI — check with `jwt.io` on a real issued token
- [ ] **Cloudflare Tunnel is routing:** `curl https://your-public-domain.com` reaches your pod — verify before OAuth testing
- [ ] **Port 443 only:** Server is accessible without a port number in the URL — required for Claude.ai web

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| GitHub-as-auth-server misconception | HIGH | Redesign auth layer; implement your own authorization server wrapping GitHub; retest all OAuth flows |
| Wrong WWW-Authenticate format | LOW | Update 401 response header; no other changes needed |
| DCR grant_types bug in SDK | LOW | Upgrade SDK or implement custom DCR handler; retest registration |
| PVC stuck in Pending | MEDIUM | Install local-path-provisioner; delete and recreate PVC; restart pod |
| Cloudflare Tunnel crash loop | LOW | Fix parameter ordering in cloudflared deployment manifest; redeploy |
| about:blank Claude.ai web bug | LOW | Switch to Claude Code CLI for testing; flag as known issue; verify spec compliance with Inspector |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| GitHub doesn't support DCR | OAuth Authorization Server design | `curl POST /oauth/register` returns client_id |
| about:blank Claude.ai web bug | Integration testing | Use Claude Code CLI as primary test client |
| Wrong WWW-Authenticate format | MCP server + OAuth implementation | `curl /mcp` without token returns correct 401 header |
| DCR grant_types validation bug | OAuth Authorization Server implementation | `curl POST /oauth/register` with `grant_types: ["authorization_code"]` succeeds |
| Python SDK RFC 9728 path bug | MCP server implementation | `curl /.well-known/oauth-protected-resource` returns valid JSON |
| redirect_uri mismatch | OAuth Authorization Server implementation | DCR stores received redirect_uris; token exchange validates them dynamically |
| No default StorageClass on Talos | Kubernetes infrastructure setup | `kubectl get storageclass` before creating PVCs |
| Cloudflare TLS confusion | Cloudflare Tunnel setup | Public URL works with HTTPS; internal routing uses HTTP |
| Cloudflare parameter ordering | Cloudflare Tunnel deployment | cloudflared pod is Running, not CrashLoopBackOff |
| Port 443 requirement | Cloudflare Tunnel configuration | Server URL has no port suffix |
| Secrets are base64 not encrypted | Kubernetes secrets phase | No Secret manifests committed to git |
| SSE transport deprecated | MCP server implementation | Server uses streamable-http transport |
| Token not validated for audience | Token validation implementation | Decoded JWT aud matches server canonical URI |

---

## Sources

- [MCP Authorization Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization) — HIGH confidence (official spec)
- [Evolving OAuth Client Registration in MCP](http://blog.modelcontextprotocol.io/posts/client_registration/) — HIGH confidence (official MCP blog)
- [Claude Help Center: Building Custom Connectors via Remote MCP Servers](https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers) — HIGH confidence (official Anthropic docs)
- [Dynamic Client Registration not supported — github/github-mcp-server issue #1404](https://github.com/github/github-mcp-server/issues/1404) — HIGH confidence (official issue confirming GitHub does not support DCR)
- [Claude OAuth requires DCR, making Azure AD/Entra ID complex — anthropics/claude-code issue #2527](https://github.com/anthropics/claude-code/issues/2527) — HIGH confidence (confirmed DCR requirement with recovery patterns)
- [Claude Desktop and claude.ai fail with about:blank loop — anthropics/claude-code issue #11814](https://github.com/anthropics/claude-code/issues/11814) — HIGH confidence (active bug report with multiple reproductions)
- [MCP OAuth using wrong redirect_uri — anthropics/claude-code issue #10439](https://github.com/anthropics/claude-code/issues/10439) — HIGH confidence (active bug report)
- [FastMCP DCR grant_types validation bug — jlowin/fastmcp issue #2460](https://github.com/jlowin/fastmcp/issues/2460) — HIGH confidence (confirmed library bug)
- [Python SDK RFC 9728 path bug — modelcontextprotocol/python-sdk issue #1052](https://github.com/modelcontextprotocol/python-sdk/issues/1052) — HIGH confidence (open SDK issue)
- [OAuth works with Inspector but not Claude — PrefectHQ/fastmcp issue #972](https://github.com/PrefectHQ/fastmcp/issues/972) — MEDIUM confidence (community report with analysis)
- [Talos Local Storage documentation](https://docs.siderolabs.com/kubernetes-guides/csi/local-storage) — HIGH confidence (official Talos docs)
- [Cloudflare Tunnel Kubernetes deployment guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/deployment-guides/kubernetes/) — HIGH confidence (official Cloudflare docs)
- [MCP auth implementation guide — Logto blog](https://blog.logto.io/mcp-auth-implementation-guide-2025-06-18) — MEDIUM confidence (verified against official spec)
- [DCR in MCP: What it is, why it exists — WorkOS](https://workos.com/blog/dynamic-client-registration-dcr-mcp-oauth) — MEDIUM confidence (verified independently)
- [MCP OAuth troubleshooting — Scalekit docs](https://docs.scalekit.com/authenticate/mcp/troubleshooting/) — MEDIUM confidence (vendor docs, independently plausible)

---
*Pitfalls research for: Remote MCP server with OAuth 2.1 (Python, Talos K8s, Cloudflare Tunnel)*
*Researched: 2026-03-02*
