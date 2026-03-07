IMAGE := "ghcr.io/hellothisisflo/sketchpad"
NS    := "sketchpad"
SHA   := `git rev-parse --short HEAD`
TAG   := "sha-" + SHA

# Show available recipes
default:
    @just --list

# --- Run ---

# Start tunnel + server together (Ctrl-C stops both)
[group('run')]
dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    just tunnel &
    just server &
    wait

# Start Cloudflare tunnel for local dev
[group('run')]
tunnel:
    cloudflared tunnel run

# Run local dev server
[group('run')]
server:
    uv run python -m sketchpad

# --- Check ---

# Run pytest test suite
[group('check')]
test:
    uv run pytest

# Run ruff linter
[group('check')]
lint:
    uv run ruff check .

# Format Python files with ruff
[group('check')]
fmt:
    uv run ruff format .

# --- Build ---

# Build Docker image for linux/amd64
[group('build')]
build:
    docker buildx build --platform linux/amd64 -t {{IMAGE}}:{{TAG}} -t {{IMAGE}}:latest --load .

# --- K8s ---

# Deploy to Kubernetes cluster
[group('k8s')]
deploy:
    kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Restart deployment (rolling)
[group('k8s')]
restart:
    kubectl rollout restart deployment/sketchpad -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Show pod and service status
[group('k8s')]
status:
    kubectl get pods -n {{NS}}
    kubectl get svc -n {{NS}}

# Tail application logs
[group('k8s')]
logs:
    kubectl logs -f -l app=sketchpad -n {{NS}} --tail=100
