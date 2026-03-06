IMAGE := "ghcr.io/hellothisisflo/sketchpad"
NS    := "sketchpad"
SHA   := `git rev-parse --short HEAD`
TAG   := "sha-" + SHA

# Show available recipes
default:
    @just --list

# --- Build ---

# Build Docker image for linux/amd64
build:
    docker buildx build --platform linux/amd64 -t {{IMAGE}}:{{TAG}} -t {{IMAGE}}:latest --load .

# --- Dev ---

# Run pytest test suite
test:
    uv run pytest

# Run ruff linter
lint:
    uv run ruff check .

# Format Python files with ruff
fmt:
    uv run ruff format .

# Run local dev server
dev:
    uv run python -m sketchpad

# --- K8s ---

# Deploy to Kubernetes cluster
deploy:
    kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Restart deployment (rolling)
restart:
    kubectl rollout restart deployment/sketchpad -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Show pod and service status
status:
    kubectl get pods -n {{NS}}
    kubectl get svc -n {{NS}}

# Tail application logs
logs:
    kubectl logs -f -l app=sketchpad -n {{NS}} --tail=100
