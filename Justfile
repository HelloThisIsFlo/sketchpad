IMAGE := "ghcr.io/hellothisisflo/sketchpad"
NS    := "sketchpad"
SHA   := `git rev-parse --short HEAD`
TAG   := "sha-" + SHA

# Show available recipes
default:
    @just --list

# --- Build ---

# Build Docker image for linux/amd64
[group('build')]
build:
    docker buildx build --platform linux/amd64 -t {{IMAGE}}:{{TAG}} -t {{IMAGE}}:latest --load .

# --- Dev ---

# Run pytest test suite
[group('dev')]
test:
    uv run pytest

# Run ruff linter
[group('dev')]
lint:
    uv run ruff check .

# Format Python files with ruff
[group('dev')]
fmt:
    uv run ruff format .

# Run local dev server
[group('dev')]
dev:
    uv run python -m sketchpad

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
