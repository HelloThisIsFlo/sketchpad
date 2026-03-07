# Phase 1: Infrastructure - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Kubernetes namespace, Secrets, NFS-backed StorageClass, PVC, cloudflared deployment, and Cloudflare Tunnel route yielding a reachable HTTPS endpoint at `sketchpad.kempenich.ai` — ready to host the MCP server with zero infrastructure surprises. Includes step-by-step setup guides for all manual prerequisites.

</domain>

<decisions>
## Implementation Decisions

### Tunnel & Hostname
- Deploy cloudflared as a Kubernetes Deployment in the `sketchpad` namespace (new tunnel, not the existing non-K8s tunnel)
- Public hostname: `sketchpad.kempenich.ai`
- Per-service subdomain pattern — no ingress controller, cloudflared routes directly to the K8s Service
- Domain: `kempenich.dev` (managed in Cloudflare), follows existing `thehome-*` naming convention

### Storage
- NFS from the start — not local-path-provisioner
- Synology NAS at `192.168.0.102` as NFS backend
- NFS service already enabled on Synology (existing export: `/volume1/Plex`)
- New dedicated shared folder needed for K8s data (e.g., `/volume1/k8s`)
- Deploy `nfs-subdir-external-provisioner` for dynamic PersistentVolume creation
- PVC backed by NFS — data survives pod restarts AND cluster teardown/rebuild
- Synology NFS share must be added to Hyper Backup for disaster recovery

### Test Endpoint
- Deploy nginx placeholder pod to verify full tunnel chain (cloudflared -> Service -> Pod)
- Proves `curl https://sketchpad.kempenich.ai/` returns HTTP response before Phase 2
- Placeholder response details: Claude's discretion

### Documentation
- Step-by-step guides with exact URLs to each settings page
- Verification steps after each action ("After saving, you should see...")
- Target DSM 7.2 for Synology NFS guide
- Three guides:
  1. `docs/github-oauth-app.md` — Creating the GitHub OAuth App, callback URL, copying credentials
  2. `docs/synology-nfs.md` — Enabling NFS, creating K8s share, permissions for cluster IP range, Hyper Backup reminder
  3. `docs/cloudflare-tunnel.md` — Creating tunnel, configuring hostname route, deploying cloudflared to K8s

### Claude's Discretion
- Nginx placeholder response format (generic 200 vs JSON health check)
- NFS shared folder naming convention on Synology
- K8s manifest organization (single file vs per-resource)
- cloudflared Deployment resource limits
- NFS provisioner configuration details (reclaimPolicy, archiveOnDelete, etc.)

</decisions>

<specifics>
## Specific Ideas

- "I want things to be as idempotent as possible and stored in one place" — NFS on Synology chosen specifically so cluster VMs can be destroyed and recreated without data loss
- "Make sure this share is going to be added to the backup" — Hyper Backup reminder is a must in the Synology NFS guide
- Existing naming pattern: `thehome-haos.kempenich.dev`, `thehome-pm.kempenich.dev` — sketchpad follows this convention

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — project is a blank slate, no code exists yet

### Established Patterns
- None — this is the first phase, patterns will be established here

### Integration Points
- Cluster: 1 control-plane (`talos-0vc-3yg`) + 2 workers (`talos-75v-99s`, `talos-7w1-nrj`), Talos v1.9.2, K8s v1.32.0
- Existing namespace: `mailroom` (separate project, don't touch)
- No existing StorageClass — Phase 1 creates the first one
- Synology NAS: `192.168.0.102`, NFS enabled, DSM 7.2
- Cluster nodes on same subnet as NAS (192.168.0.x) — direct NFS access, no routing needed

</code_context>

<deferred>
## Deferred Ideas

- Synology NAS as general K8s storage strategy (explore further for Obsidian vault project)
- Ingress controller for cluster-wide routing — revisit if many services end up on the cluster
- local-path-provisioner as secondary StorageClass for ephemeral/cache workloads

</deferred>

---

*Phase: 01-infrastructure*
*Context gathered: 2026-03-03*
