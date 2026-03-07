# Phase 1: Infrastructure - Research

**Researched:** 2026-03-03
**Domain:** Kubernetes infrastructure (NFS storage, Cloudflare Tunnel, Secrets, container registry)
**Confidence:** HIGH

## Summary

Phase 1 provisions all Kubernetes infrastructure for the Sketchpad MCP server: an NFS-backed StorageClass using `nfs-subdir-external-provisioner` with a Synology NAS backend, a `cloudflared` Deployment creating a Cloudflare Tunnel to expose the service at `sketchpad.kempenich.ai`, Kubernetes Secrets for GitHub OAuth credentials and encryption keys, a container image pushed to GitHub Container Registry (ghcr.io), and an nginx placeholder to verify the full tunnel chain. Three documentation guides are also produced.

The infrastructure is entirely standard Kubernetes -- no exotic tooling. The NFS provisioner is a well-maintained Helm chart from kubernetes-sigs, cloudflared has an official Kubernetes deployment guide from Cloudflare, and ghcr.io is the natural choice for a GitHub-hosted project. The Talos OS cluster has built-in NFS client support in its kubelet image, so no node-level configuration is needed. The Synology NAS is on the same subnet as cluster nodes, eliminating routing concerns.

**Primary recommendation:** Use Helm for the NFS provisioner (it handles RBAC, leader election, and StorageClass creation), raw manifests for cloudflared and nginx (simple enough to not need Helm), and `kubectl create secret` for credentials.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Deploy cloudflared as a Kubernetes Deployment in the `sketchpad` namespace (new tunnel, not the existing non-K8s tunnel)
- Public hostname: `sketchpad.kempenich.ai`
- Per-service subdomain pattern -- no ingress controller, cloudflared routes directly to the K8s Service
- Domain: `kempenich.dev` (managed in Cloudflare), follows existing `thehome-*` naming convention
- NFS from the start -- not local-path-provisioner
- Synology NAS at `192.168.0.102` as NFS backend
- NFS service already enabled on Synology (existing export: `/volume1/Plex`)
- New dedicated shared folder needed for K8s data (e.g., `/volume1/k8s`)
- Deploy `nfs-subdir-external-provisioner` for dynamic PersistentVolume creation
- PVC backed by NFS -- data survives pod restarts AND cluster teardown/rebuild
- Synology NFS share must be added to Hyper Backup for disaster recovery
- Deploy nginx placeholder pod to verify full tunnel chain (cloudflared -> Service -> Pod)
- Proves `curl https://sketchpad.kempenich.ai/` returns HTTP response before Phase 2
- Step-by-step guides with exact URLs to each settings page
- Verification steps after each action ("After saving, you should see...")
- Target DSM 7.2 for Synology NFS guide
- Three guides: `docs/github-oauth-app.md`, `docs/synology-nfs.md`, `docs/cloudflare-tunnel.md`

### Claude's Discretion
- Nginx placeholder response format (generic 200 vs JSON health check)
- NFS shared folder naming convention on Synology
- K8s manifest organization (single file vs per-resource)
- cloudflared Deployment resource limits
- NFS provisioner configuration details (reclaimPolicy, archiveOnDelete, etc.)

### Deferred Ideas (OUT OF SCOPE)
- Synology NAS as general K8s storage strategy (explore further for Obsidian vault project)
- Ingress controller for cluster-wide routing -- revisit if many services end up on the cluster
- local-path-provisioner as secondary StorageClass for ephemeral/cache workloads
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Server is deployed as a Kubernetes Deployment with a ClusterIP Service | Nginx placeholder Deployment + ClusterIP Service pattern; replaced by actual server in Phase 3 |
| INFRA-02 | Sketchpad file persists across pod restarts via PersistentVolumeClaim | NFS-backed StorageClass via nfs-subdir-external-provisioner; PVC with ReadWriteOnce or ReadWriteMany |
| INFRA-03 | OAuth state persists across pod restarts via PVC-backed store | Same NFS StorageClass; separate PVC or shared PVC with subPath |
| INFRA-04 | GitHub OAuth App credentials and other secrets stored as Kubernetes Secrets | `kubectl create secret generic` with --from-literal for client_id, client_secret, fernet key |
| INFRA-05 | Server is accessible over HTTPS via Cloudflare Tunnel | cloudflared Deployment with tunnel token from Secret, routing to ClusterIP Service |
| INFRA-06 | Container image is built and pushed to a registry accessible by the cluster | ghcr.io public repository; no imagePullSecret needed for public images |
| DOCS-02 | Guide for creating the GitHub OAuth App | Step-by-step with exact GitHub URLs, callback URL, credential extraction |
| DOCS-03 | Guide for configuring Cloudflare Tunnel | Dashboard tunnel creation, hostname routing, token extraction, K8s manifest |
</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| nfs-subdir-external-provisioner | Helm chart 4.0.18 (image v4.0.2) | Dynamic NFS PV provisioner | Official kubernetes-sigs project; standard for NFS-backed dynamic provisioning |
| cloudflared | 2026.2.0 (latest) | Cloudflare Tunnel connector | Official Cloudflare image with K8s deployment guide |
| nginx | 1.27-alpine | Placeholder test pod | Smallest standard web server image |
| Helm 3 | 3.x (on local machine) | Install NFS provisioner chart | Standard K8s package manager; handles RBAC/StorageClass creation |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| kubectl | matches K8s 1.32 | Apply manifests, create secrets | All K8s operations |
| docker/podman | local | Build and push container image | INFRA-06 container registry push |
| ghcr.io | N/A | Container image registry | Public image hosting for GitHub projects |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nfs-subdir-external-provisioner | synology-csi-talos | More features (iSCSI, snapshots) but much more complex setup; overkill for single PVC |
| nfs-subdir-external-provisioner | Longhorn | Better for multi-node replication but requires dedicated disks; NAS already provides redundancy |
| Helm install | Raw manifests | More manual work; would need to write RBAC, ServiceAccount, StorageClass by hand |
| ghcr.io | Docker Hub | Docker Hub has pull rate limits; ghcr.io is natural for GitHub-hosted project |

**Installation:**
```bash
# NFS provisioner via Helm
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace sketchpad \
  --set nfs.server=192.168.0.102 \
  --set nfs.path=/volume1/k8s \
  --set storageClass.name=nfs-client \
  --set storageClass.reclaimPolicy=Retain \
  --set storageClass.archiveOnDelete=false

# cloudflared and nginx: raw kubectl apply (no Helm needed)
```

## Architecture Patterns

### Recommended Project Structure
```
k8s/
  namespace.yaml          # Namespace definition
  nfs-provisioner/        # Helm values override (if needed)
    values.yaml
  cloudflared/
    deployment.yaml       # cloudflared Deployment
    secret.yaml           # Tunnel token (template/reference only, not committed)
  placeholder/
    deployment.yaml       # nginx Deployment + Service
  secrets/
    README.md             # Instructions for creating secrets (no actual secrets)
  pvc.yaml                # PersistentVolumeClaim(s)
docs/
  github-oauth-app.md
  synology-nfs.md
  cloudflare-tunnel.md
```

### Pattern 1: Namespace Isolation
**What:** All resources in a dedicated `sketchpad` namespace
**When to use:** Always -- project constraint
**Example:**
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sketchpad
```

### Pattern 2: Remotely-Managed Cloudflare Tunnel
**What:** Tunnel configuration managed in Cloudflare dashboard, cloudflared only needs a token
**When to use:** When hostname routing is configured in the dashboard (not in a local config file)
**Example:**
```yaml
# k8s/cloudflared/deployment.yaml
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
          image: cloudflare/cloudflared:2026.2.0
          args:
            - tunnel
            - --no-autoupdate
            - --metrics
            - 0.0.0.0:2000
            - run
          env:
            - name: TUNNEL_TOKEN
              valueFrom:
                secretKeyRef:
                  name: cloudflared-tunnel-token
                  key: token
          livenessProbe:
            httpGet:
              path: /ready
              port: 2000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "200m"
```

### Pattern 3: NFS-Backed Dynamic Provisioning
**What:** Helm-installed provisioner creates PVs automatically when PVCs are created
**When to use:** When you want dynamic PV creation from a single NFS share
**Example:**
```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: sketchpad-data
  namespace: sketchpad
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: nfs-client
  resources:
    requests:
      storage: 1Gi
```

### Pattern 4: Nginx Placeholder with JSON Health Response
**What:** Simple nginx pod returning a JSON health check, proving the full tunnel chain works
**When to use:** Before the real application is deployed
**Recommendation:** Return a JSON health check response rather than generic nginx welcome page -- makes it easy to verify programmatically and clearly signals "this is intentional, not a misconfiguration."
**Example:**
```yaml
# k8s/placeholder/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sketchpad-placeholder
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
        - name: nginx
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
          volumeMounts:
            - name: config
              mountPath: /etc/nginx/conf.d/default.conf
              subPath: default.conf
            - name: health
              mountPath: /usr/share/nginx/html/health.json
              subPath: health.json
      volumes:
        - name: config
          configMap:
            name: placeholder-config
        - name: health
          configMap:
            name: placeholder-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: placeholder-config
  namespace: sketchpad
data:
  default.conf: |
    server {
      listen 80;
      location / {
        default_type application/json;
        return 200 '{"status":"ok","service":"sketchpad","phase":"infrastructure-placeholder"}';
      }
    }
---
apiVersion: v1
kind: Service
metadata:
  name: sketchpad
  namespace: sketchpad
spec:
  selector:
    app: sketchpad
  ports:
    - port: 80
      targetPort: 80
  type: ClusterIP
```

### Anti-Patterns to Avoid
- **Committing secrets to git:** Never put actual secret values in manifest files. Use `kubectl create secret` or document the commands in a README.
- **Using `latest` tag for cloudflared:** Pin to a specific version (e.g., `2026.2.0`) to avoid unexpected breaking changes on pod restart.
- **Setting `storageClass.reclaimPolicy=Delete` for persistent data:** Use `Retain` so data survives PVC deletion. The NFS provisioner's `archiveOnDelete` is a secondary safety net.
- **Creating the NFS share with restrictive squash settings:** Kubernetes pods run as various UIDs; use "Map all users to admin" squash on Synology to avoid permission denied errors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NFS StorageClass + RBAC | Manual PV, SA, ClusterRole, ClusterRoleBinding | `nfs-subdir-external-provisioner` Helm chart | Handles 6+ resources, leader election, RBAC automatically |
| Dynamic PV provisioning | Static PV per PVC | Helm-installed provisioner with StorageClass | Static PVs don't scale and require manual cleanup |
| Cloudflare Tunnel routing | Ingress controller + cert-manager | cloudflared with remotely-managed tunnel | Single binary, HTTPS terminated at Cloudflare edge, zero cert management |
| Fernet key generation | Manual base64 encoding | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Correct format guaranteed (URL-safe base64, 32 bytes) |

**Key insight:** Phase 1 is all infrastructure glue -- every component has an official, well-documented deployment path. The value is in getting the configuration right, not in building custom solutions.

## Common Pitfalls

### Pitfall 1: NFS Permission Denied on Synology
**What goes wrong:** Pods get "permission denied" when writing to the NFS-backed PVC.
**Why it happens:** Synology's default NFS squash setting is "No mapping," which preserves the client's UID/GID. Kubernetes pods may run as arbitrary UIDs that don't exist on the Synology.
**How to avoid:** When creating the NFS permission rule on the Synology shared folder, set Squash to "Map all users to admin." This gives all NFS clients admin-equivalent access to that specific share.
**Warning signs:** Pod logs show "Permission denied" on file write; pod stays in CrashLoopBackOff.

### Pitfall 2: NFS Provisioner Namespace Scope
**What goes wrong:** The Helm chart installs RBAC resources (ClusterRole, ClusterRoleBinding) cluster-wide, but the provisioner pod runs in the specified namespace.
**Why it happens:** Dynamic provisioning requires cluster-level permissions to watch PVCs across namespaces.
**How to avoid:** Install with `--namespace sketchpad` but understand the RBAC is cluster-scoped. This is normal and expected. If re-installing, `helm uninstall` first to clean up cluster-scoped resources.
**Warning signs:** PVCs stay in Pending state; provisioner pod logs show RBAC permission errors.

### Pitfall 3: Cloudflare Tunnel Hostname Not Configured
**What goes wrong:** cloudflared pod is Running but `curl https://sketchpad.kempenich.ai/` returns a Cloudflare error page (e.g., 1033).
**Why it happens:** The tunnel was created in the dashboard but no public hostname route was added pointing to the K8s Service.
**How to avoid:** In the Cloudflare dashboard, after creating the tunnel, add a Public Hostname entry: subdomain `thehome-sketchpad`, domain `kempenich.dev`, service `http://sketchpad.sketchpad.svc.cluster.local:80`. The service URL uses K8s DNS: `<service-name>.<namespace>.svc.cluster.local`.
**Warning signs:** cloudflared logs show "connected" but HTTP requests to the hostname return Cloudflare error codes.

### Pitfall 4: cloudflared Can't Resolve K8s Service DNS
**What goes wrong:** cloudflared pod starts, connects to Cloudflare, but requests to the hostname return 502 Bad Gateway.
**Why it happens:** The hostname route in the dashboard points to a service name that doesn't exist yet, or uses the wrong namespace in the DNS name.
**How to avoid:** The service URL in the Cloudflare dashboard must match the actual K8s Service. Format: `http://<service-name>.<namespace>.svc.cluster.local:<port>`. For the placeholder: `http://sketchpad.sketchpad.svc.cluster.local:80`.
**Warning signs:** 502 errors from Cloudflare; cloudflared logs show connection refused or DNS resolution failure.

### Pitfall 5: ghcr.io Image Visibility
**What goes wrong:** Kubernetes nodes can't pull the container image from ghcr.io -- `ImagePullBackOff`.
**Why it happens:** New packages on ghcr.io default to private visibility. If the image is private, K8s nodes need an imagePullSecret.
**How to avoid:** After the first push, go to GitHub > Packages > select the package > Package settings > Change visibility to Public. Alternatively, create an imagePullSecret, but public is simpler for this project.
**Warning signs:** Pod stuck in `ImagePullBackOff`; `kubectl describe pod` shows "unauthorized" in events.

### Pitfall 6: Helm Not Installed
**What goes wrong:** `helm` command not found when trying to install the NFS provisioner.
**Why it happens:** Talos clusters don't include Helm; it runs on the local machine that has `kubectl` access.
**How to avoid:** Verify `helm version` on the local machine before starting. Install with `brew install helm` on macOS if needed.
**Warning signs:** Command not found error.

### Pitfall 7: NFS Provisioner Pod Can't Mount NFS Share
**What goes wrong:** The nfs-subdir-external-provisioner pod itself gets stuck in ContainerCreating with mount errors.
**Why it happens:** The NFS share path doesn't exist on the Synology, or the Synology NFS permission rule doesn't include the cluster node IPs.
**How to avoid:** Create the shared folder on Synology FIRST, then add an NFS permission rule with the cluster subnet (e.g., `192.168.0.0/24`). Verify with `showmount -e 192.168.0.102` from a cluster node or test machine.
**Warning signs:** `kubectl describe pod` shows "mount.nfs: access denied" or "mount.nfs: No such file or directory."

## Code Examples

Verified patterns from official sources:

### Creating the Namespace
```bash
kubectl create namespace sketchpad
```

### Installing NFS Provisioner via Helm
```bash
# Source: https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner/blob/master/charts/nfs-subdir-external-provisioner/README.md
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace sketchpad \
  --set nfs.server=192.168.0.102 \
  --set nfs.path=/volume1/k8s \
  --set storageClass.name=nfs-client \
  --set storageClass.defaultClass=false \
  --set storageClass.reclaimPolicy=Retain \
  --set storageClass.archiveOnDelete=false \
  --set storageClass.accessModes=ReadWriteOnce
```

### Creating Kubernetes Secrets
```bash
# GitHub OAuth App credentials (user provides these after creating the app)
kubectl create secret generic github-oauth \
  --namespace sketchpad \
  --from-literal=client-id='<GITHUB_CLIENT_ID>' \
  --from-literal=client-secret='<GITHUB_CLIENT_SECRET>'

# Fernet encryption key for OAuth state persistence
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
kubectl create secret generic encryption-key \
  --namespace sketchpad \
  --from-literal=fernet-key="$FERNET_KEY"

# Cloudflare Tunnel token
kubectl create secret generic cloudflared-tunnel-token \
  --namespace sketchpad \
  --from-literal=token='<TUNNEL_TOKEN>'
```

### Verifying Storage Is Working
```bash
# Check StorageClass exists
kubectl get storageclass nfs-client

# Check PVC is Bound
kubectl get pvc -n sketchpad

# Check provisioner pod is running
kubectl get pods -n sketchpad -l app=nfs-subdir-external-provisioner
```

### Verifying Cloudflare Tunnel
```bash
# Check cloudflared pod is running
kubectl get pods -n sketchpad -l app=cloudflared

# Check cloudflared logs for "connected" messages
kubectl logs -n sketchpad -l app=cloudflared --tail=20

# Test the public endpoint
curl -I https://sketchpad.kempenich.ai/
```

### Pushing to ghcr.io
```bash
# Authenticate (one-time setup with a PAT that has packages:write scope)
echo $GITHUB_PAT | docker login ghcr.io -u <USERNAME> --password-stdin

# Build and push (image name MUST be lowercase)
docker build -t ghcr.io/<owner>/sketchpad:latest .
docker push ghcr.io/<owner>/sketchpad:latest

# After push: set package visibility to Public on GitHub
# GitHub > Your profile > Packages > sketchpad > Package settings > Change visibility
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NFS in-tree provisioner | nfs-subdir-external-provisioner (out-of-tree) | K8s 1.23+ | In-tree NFS provisioner removed; must use external provisioner |
| Locally-managed Cloudflare Tunnel (config file) | Remotely-managed tunnel (dashboard + token) | 2022 | Simpler setup; config lives in Cloudflare dashboard, not on the client |
| Docker Hub for images | ghcr.io for GitHub projects | 2020+ | No pull rate limits for public images; better integration with GitHub |
| HostPath volumes on Talos | External storage (NFS, CSI) | Talos design | Talos is immutable; local storage is ephemeral by design |

**Deprecated/outdated:**
- In-tree NFS provisioner: Removed from Kubernetes; the external provisioner is the replacement
- Locally-managed Cloudflare tunnels (credential JSON files): Still work but remotely-managed is recommended for simpler setup
- `nfs-client-provisioner` (old Helm chart name): Renamed to `nfs-subdir-external-provisioner`

## Open Questions

1. **Helm availability on local machine**
   - What we know: Helm runs locally (not on cluster nodes). macOS can install via `brew install helm`.
   - What's unclear: Whether user already has Helm installed.
   - Recommendation: Add a pre-flight check (`helm version`) at the start of the plan. If missing, install it.

2. **NFS protocol version on Synology**
   - What we know: Synology DSM 7.2 supports NFS v3 and v4.1. Talos kubelet includes NFS client.
   - What's unclear: Which NFS version Talos kubelet supports. Default is usually v4.
   - Recommendation: Enable NFS 4.1 on Synology (maximum protocol version). Don't specify `nfs.mountOptions` in Helm values unless issues arise -- let the client negotiate.

3. **Shared folder name on Synology**
   - What we know: User wants a new dedicated folder (e.g., `/volume1/k8s`).
   - What's unclear: Whether `k8s` is the best name or if it should be more specific.
   - Recommendation: Use `/volume1/k8s` -- generic enough for future expansion to other K8s workloads. The NFS provisioner creates subdirectories automatically per PVC.

4. **Single PVC vs two PVCs for INFRA-02 and INFRA-03**
   - What we know: INFRA-02 (sketchpad file) and INFRA-03 (OAuth state) both need persistence.
   - What's unclear: Whether to use one PVC with subPaths or two separate PVCs.
   - Recommendation: Two separate PVCs. Cleaner separation of concerns, easier to reason about, and the NFS provisioner handles the subdirectory creation automatically. Cost is negligible (just subdirectories on the same NFS share).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Shell commands (kubectl, curl, helm) |
| Config file | None -- infrastructure validation is command-based |
| Quick run command | `kubectl get all -n sketchpad` |
| Full suite command | See per-requirement commands below |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | Deployment + ClusterIP Service exist | smoke | `kubectl get deployment sketchpad-placeholder -n sketchpad && kubectl get svc sketchpad -n sketchpad` | N/A (kubectl) |
| INFRA-02 | Sketchpad PVC is Bound | smoke | `kubectl get pvc sketchpad-data -n sketchpad -o jsonpath='{.status.phase}'` (expect "Bound") | N/A |
| INFRA-03 | OAuth state PVC is Bound | smoke | `kubectl get pvc sketchpad-state -n sketchpad -o jsonpath='{.status.phase}'` (expect "Bound") | N/A |
| INFRA-04 | Secrets exist | smoke | `kubectl get secret github-oauth encryption-key cloudflared-tunnel-token -n sketchpad` | N/A |
| INFRA-05 | HTTPS endpoint reachable | integration | `curl -sf -o /dev/null -w '%{http_code}' https://sketchpad.kempenich.ai/` (expect "200") | N/A |
| INFRA-06 | Container image in registry | smoke | `docker pull ghcr.io/<owner>/sketchpad:latest` or verify push log | N/A |
| DOCS-02 | GitHub OAuth guide exists | file-check | `test -f docs/github-oauth-app.md` | Wave 0 |
| DOCS-03 | Cloudflare Tunnel guide exists | file-check | `test -f docs/cloudflare-tunnel.md` | Wave 0 |

### Sampling Rate
- **Per task commit:** `kubectl get all -n sketchpad` + relevant resource check
- **Per wave merge:** Full suite of all smoke/integration commands above
- **Phase gate:** All commands above pass before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `docs/github-oauth-app.md` -- covers DOCS-02
- [ ] `docs/synology-nfs.md` -- additional guide per CONTEXT.md decisions
- [ ] `docs/cloudflare-tunnel.md` -- covers DOCS-03
- [ ] Namespace `sketchpad` must be created first
- [ ] Helm must be available locally (`helm version`)

## Sources

### Primary (HIGH confidence)
- [nfs-subdir-external-provisioner Helm chart README](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner/blob/master/charts/nfs-subdir-external-provisioner/README.md) - Helm values, installation commands, configuration options
- [Cloudflare Tunnel Kubernetes deployment guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/deployment-guides/kubernetes/) - Official manifest, Secret pattern, liveness probe, replica guidance
- [Cloudflare Tunnel dashboard creation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/) - Token-based remotely managed tunnel setup
- [Talos OS storage documentation](https://docs.siderolabs.com/kubernetes-guides/csi/storage) - NFS client built into kubelet image, supported storage solutions
- [GitHub Container Registry docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) - Authentication, pushing, visibility settings
- [Synology DSM NFS permissions](https://kb.synology.com/en-global/DSM/help/DSM/AdminCenter/file_share_privilege_nfs?version=7) - NFS rule configuration, squash options
- [Fernet encryption documentation](https://cryptography.io/en/latest/fernet/) - Key generation, format specification

### Secondary (MEDIUM confidence)
- [cloudflare/cloudflared Docker Hub](https://hub.docker.com/r/cloudflare/cloudflared/tags) - Current image version tags (2026.2.0)
- [Configuring Synology NAS as NFS Storage for Kubernetes](https://medium.com/@bastian.ohm/configuring-your-synology-nas-as-nfs-storage-for-kubernetes-cluster-5e668169e5a2) - Step-by-step Synology NFS setup for K8s
- [Kubernetes Secrets documentation](https://kubernetes.io/docs/concepts/configuration/secret/) - base64 encoding, secret creation patterns

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools are official kubernetes-sigs or vendor projects with stable APIs
- Architecture: HIGH - Standard Kubernetes patterns (Deployment, Service, PVC, Secret, ConfigMap)
- Pitfalls: HIGH - Well-documented failure modes from official docs and community experience
- NFS on Talos: MEDIUM - NFS client is confirmed built-in, but Talos docs discourage NFS (user decision overrides)
- cloudflared version: MEDIUM - Docker Hub tags confirmed 2026.2.0 exists, but may not be absolute latest

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days -- all components are stable)
