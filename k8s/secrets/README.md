# Kubernetes Secrets

**Never commit actual secret values to git.** Run these commands interactively.

## Prerequisites

- `kubectl` configured to talk to your cluster
- Namespace `sketchpad` exists: `kubectl apply -f k8s/namespace.yaml`

## 1. GitHub OAuth App Credentials

After creating the GitHub OAuth App (see `docs/github-oauth-app.md`), create the secret with the Client ID and Client Secret you copied:

```bash
kubectl create secret generic github-oauth \
  --namespace sketchpad \
  --from-literal=client-id='<YOUR_GITHUB_CLIENT_ID>' \
  --from-literal=client-secret='<YOUR_GITHUB_CLIENT_SECRET>'
```

Replace `<YOUR_GITHUB_CLIENT_ID>` and `<YOUR_GITHUB_CLIENT_SECRET>` with the actual values from your GitHub OAuth App.

## 2. Fernet Encryption Key

The encryption key protects OAuth state data at rest. Generate a key and create the secret in one step:

```bash
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
kubectl create secret generic encryption-key \
  --namespace sketchpad \
  --from-literal=fernet-key="$FERNET_KEY"
```

This generates a cryptographically secure Fernet key (URL-safe base64, 32 bytes) and stores it as a Kubernetes Secret.

## 3. Cloudflare Tunnel Token

After creating the Cloudflare Tunnel (see `docs/cloudflare-tunnel.md`), create the secret with the tunnel token you copied:

```bash
kubectl create secret generic cloudflared-tunnel-token \
  --namespace sketchpad \
  --from-literal=token='<YOUR_TUNNEL_TOKEN>'
```

Replace `<YOUR_TUNNEL_TOKEN>` with the token from the Cloudflare dashboard (the long string starting with `ey...`).

## Verifying Secrets

After creating all three secrets, verify they exist:

```bash
kubectl get secrets -n sketchpad
```

You should see:

```
NAME                        TYPE     DATA   AGE
github-oauth                Opaque   2      ...
encryption-key              Opaque   1      ...
cloudflared-tunnel-token    Opaque   1      ...
```

To check that a secret has the expected keys (without revealing values):

```bash
kubectl describe secret github-oauth -n sketchpad
kubectl describe secret encryption-key -n sketchpad
kubectl describe secret cloudflared-tunnel-token -n sketchpad
```
