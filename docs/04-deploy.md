# Deploying to Kubernetes

This guide covers deploying the Sketchpad MCP server to Kubernetes, replacing the nginx placeholder.

## Prerequisites

- `kubectl` configured and pointing to the cluster
- Namespace `sketchpad` exists (`kubectl get ns sketchpad`)
- Secrets created: `github-oauth`, `encryption-key` (see `k8s/secrets/README.md`)
- PVCs bound: `sketchpad-data`, `sketchpad-state` (`kubectl get pvc -n sketchpad`)
- Container image pushed to `ghcr.io/hellothisisflo/sketchpad` (CI pushes on every merge to main)

## Remove the Placeholder

Delete the placeholder deployment and its ConfigMap before deploying the real server:

```bash
kubectl delete deployment sketchpad-placeholder -n sketchpad
kubectl delete configmap placeholder-config -n sketchpad
```

The placeholder Service (`sketchpad`) will be updated in-place by the next step.

## Build and Push

Use the Makefile targets to build and push the container image. This is an alternative to waiting for CI -- useful for quick iterations.

```bash
make build    # Build image tagged with git SHA + latest
make push     # Push both tags to ghcr.io
```

Or do both at once:

```bash
make build push
```

## Deploy

Apply the K8s manifests and wait for the rollout:

```bash
make deploy
```

This runs:
1. `kubectl apply` on `k8s/deployment.yaml` and `k8s/service.yaml`
2. `kubectl rollout status` with a 120s timeout

Or do everything (build + push + deploy):

```bash
make all
```

## Verify

### Pod is Running

```bash
kubectl get pods -n sketchpad
```

You should see a `sketchpad-<hash>` pod with status `Running`.

### Health Endpoint

```bash
curl -sf https://thehome-sketchpad.kempenich.dev/health
```

Expected: `{"status":"ok","service":"sketchpad"}`

### OAuth Discovery

```bash
curl -sf https://thehome-sketchpad.kempenich.dev/.well-known/oauth-authorization-server | python3 -m json.tool
```

Should return OAuth metadata with `authorization_endpoint`, `token_endpoint`, etc.

## Check Logs

```bash
kubectl logs -f deployment/sketchpad -n sketchpad
```

## Updating After Code Changes

1. Push code to `main` -- GitHub Actions CI builds and pushes the image automatically
2. Deploy the new image:

```bash
make deploy
```

The Deployment uses `imagePullPolicy: Always` with the `latest` tag, so `kubectl rollout restart` also works:

```bash
kubectl rollout restart deployment/sketchpad -n sketchpad
```

## Quick Reference

```bash
make status   # Show pods and services in the sketchpad namespace
```
