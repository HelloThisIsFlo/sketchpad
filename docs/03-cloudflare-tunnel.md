# Setting Up Cloudflare Tunnel for Sketchpad

This guide creates a Cloudflare Tunnel that routes internet traffic to the sketchpad service running in your Kubernetes cluster. The tunnel provides HTTPS access at `sketchpad.kempenich.ai` without exposing any inbound ports on your network.

## Prerequisites

- A Cloudflare account with the `kempenich.ai` domain
- Access to the Cloudflare Zero Trust dashboard

## Steps

### 1. Open the Cloudflare Zero Trust Dashboard

Go to: **<https://one.dash.cloudflare.com/>**

Navigate to **Networks** > **Tunnels** in the left sidebar.

**Verification:** You should see the Tunnels page, possibly with existing tunnels listed.

### 2. Create a New Tunnel

Click **"Create a tunnel"**.

### 3. Select the Connector Type

Select **"Cloudflared"** as the connector type.

Click **Next**.

### 4. Name the Tunnel

Enter the tunnel name: **`sketchpad`**

Click **Save tunnel**.

### 5. Copy the Tunnel Token

On the "Install and run connectors" page, you'll see installation commands for various platforms.

**Do NOT install cloudflared here** -- Kubernetes handles this via the cloudflared Deployment.

Find the token: look for the `--token` flag in any of the install commands. The token is the long string after `--token`. It starts with `ey...` and is typically several hundred characters long.

Copy the full token string.

**Verification:** You have a token string starting with `ey...` (it's a base64-encoded JSON Web Token containing the tunnel credentials).

### 6. Configure the Public Hostname

Click **Next** to go to the hostname configuration page.

Add a public hostname with these settings:

| Field | Value |
|-------|-------|
| **Subdomain** | `sketchpad` |
| **Domain** | `kempenich.ai` |
| **Path** | (leave empty) |
| **Service type** | HTTP |
| **Service URL** | `sketchpad.sketchpad.svc.cluster.local:80` |

The service URL uses Kubernetes internal DNS. The format is:

```
<service-name>.<namespace>.svc.cluster.local:<port>
```

The Service named `sketchpad` in namespace `sketchpad` on port 80 becomes `sketchpad.sketchpad.svc.cluster.local:80`.

### 7. Save the Tunnel

Click **Save tunnel**.

**Verification:** The tunnel appears in your tunnel list with status **"Inactive"**. This is expected -- the cloudflared pod hasn't been deployed to the cluster yet. The status will change to **"Healthy"** after you deploy the cloudflared Deployment in Plan 02.

### 8. Create the Kubernetes Secret

Create the Kubernetes Secret with the tunnel token you copied in step 5:

```bash
kubectl create secret generic cloudflared-tunnel-token \
  --namespace sketchpad \
  --from-literal=token='<YOUR_TUNNEL_TOKEN>'
```

Replace `<YOUR_TUNNEL_TOKEN>` with the full token string you copied (the one starting with `ey...`).

See `k8s/secrets/README.md` for all secret creation commands.

### 9. Deploy cloudflared (Plan 02)

The cloudflared Deployment manifest is at `k8s/cloudflared/deployment.yaml`. It will be applied to the cluster in Plan 02. After deployment:

1. Check the pod is running:
   ```bash
   kubectl get pods -n sketchpad -l app=cloudflared
   ```

2. Check the logs for a successful connection:
   ```bash
   kubectl logs -n sketchpad -l app=cloudflared --tail=20
   ```
   You should see messages about connecting to Cloudflare's edge.

3. Verify the tunnel status in the Cloudflare dashboard -- it should now show **"Healthy"**.

4. Test the public endpoint:
   ```bash
   curl https://sketchpad.kempenich.ai/
   ```
   You should receive the JSON placeholder response:
   ```json
   {"status":"ok","service":"sketchpad","phase":"infrastructure-placeholder"}
   ```

## How It Works

```
Internet                  Cloudflare Edge           Your Cluster
--------                  ---------------           ------------
User/Claude AI  --->  sketchpad.            --->  cloudflared pod
                      kempenich.ai                     |
                      (HTTPS termination)              v
                                                  Service: sketchpad
                                                  (ClusterIP, port 80)
                                                       |
                                                       v
                                                  Pod: sketchpad-placeholder
                                                  (nginx, port 80)
```

- **HTTPS termination** happens at Cloudflare's edge. Traffic between Cloudflare and cloudflared uses an encrypted tunnel.
- **cloudflared** creates an outbound connection to Cloudflare -- no inbound ports needed on your network (works behind CGNAT).
- **The Service URL** in the tunnel config (`sketchpad.sketchpad.svc.cluster.local:80`) tells cloudflared where to forward requests inside the cluster.

## Troubleshooting

### Tunnel shows "Inactive" after deploying cloudflared

Check the cloudflared pod logs for errors:
```bash
kubectl logs -n sketchpad -l app=cloudflared
```

Common causes:
- **Invalid token:** The secret value doesn't match the tunnel token. Delete and recreate the secret.
- **DNS resolution failure:** The pod can't resolve Cloudflare's servers. Check cluster DNS.

### curl returns Cloudflare error page (e.g., error 1033)

The tunnel is connected but the hostname route is misconfigured. In the Cloudflare dashboard:
1. Go to **Networks** > **Tunnels** > **sketchpad** > **Public Hostname**
2. Verify the service URL is `http://sketchpad.sketchpad.svc.cluster.local:80`
3. Verify the subdomain is `sketchpad` and domain is `kempenich.ai`

### curl returns 502 Bad Gateway

cloudflared can't reach the target service. Check:
1. The Service exists: `kubectl get svc sketchpad -n sketchpad`
2. The placeholder pod is running: `kubectl get pods -n sketchpad -l app=sketchpad`
3. The Service URL in the dashboard matches the Service name and namespace
