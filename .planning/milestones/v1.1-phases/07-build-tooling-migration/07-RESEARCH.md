# Phase 7: Build Tooling Migration - Research

**Researched:** 2026-03-06
**Domain:** Build tooling (Justfile), CI/CD (GitHub Actions), Python linting (Ruff)
**Confidence:** HIGH

## Summary

Phase 7 replaces the Makefile with a Justfile, adds Ruff as linter/formatter, and extends the CI pipeline with test+lint gates before Docker build. The existing Makefile has 6 recipes; 4 translate directly, 2 are removed (push, all). New dev recipes are added (test, lint, fmt, dev, logs).

Just is a mature, stable command runner (v1.46.0, Jan 2026) with clean syntax, no `.PHONY` needed, and `{{var}}` interpolation. Ruff is installed locally already (v0.15.2). The `setup-just` GitHub Action is at v3, `setup-uv` at v7. Both are straightforward to integrate.

**Primary recommendation:** Write the Justfile first, verify all recipes work locally, then do the one-time ruff format commit, then update CI, then delete the Makefile.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Translate all Makefile recipes except `push` and `all` (push is CI-only, all depended on push)
- Kept recipes: `build`, `deploy`, `restart`, `status`
- New dev recipes: `test` (wraps `uv run pytest`), `lint` (wraps `uv run ruff check`), `fmt` (wraps `uv run ruff format`), `dev` (local dev server), `logs` (kubectl logs -f)
- Only include recipes that actually work and are useful -- no stubs
- Remove `push` recipe entirely -- CI is the only path to the container registry
- Remove `all` recipe (was `build push deploy`) -- no longer makes sense without push
- Deploy recipe assumes CI has already pushed the image
- Keep Docker GitHub Actions (`docker/build-push-action`, `docker/metadata-action`) for container build+push
- Add `setup-just` action to CI workflow
- Add `just test` and `just lint` steps that must pass before Docker build+push runs (gate on both)
- CI runs: checkout -> setup-just -> setup-python/uv -> just test -> just lint -> Docker login -> Docker build+push
- Add ruff as dev dependency in pyproject.toml
- Basic ruff config in pyproject.toml (sensible defaults)
- One-time formatting commit to normalize all existing code before adding lint/format recipes
- Hardcode project constants in Justfile (IMAGE, NS) -- not .env
- Default recipe (`just` with no args) shows `just --list` -- safe and discoverable
- Lowercase recipe names with hyphens for multi-word
- Backtick expressions for shell commands (e.g., `` SHA := `git rev-parse --short HEAD` ``)
- No `.PHONY` needed -- Just recipes always run

### Claude's Discretion
- Exact ruff rule configuration (sensible defaults for a small Python project)
- Deploy recipe adjustments (now that push is CI-only)
- Dev server recipe implementation (local server start command)
- Logs recipe flags (follow, tail count, etc.)
- Whether to keep the `build` recipe for local Docker testing or simplify it

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-01 | Justfile replaces Makefile with 1:1 translation of all recipes | Justfile syntax documented; all 4 kept recipes have direct translations; new recipes use `uv run` pattern |
| BUILD-02 | GitHub Actions CI workflow uses `setup-just` action instead of `make` | `extractions/setup-just@v3` documented; `astral-sh/setup-uv@v7` for Python/test deps; CI pipeline order specified |
</phase_requirements>

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| just | 1.46.0 | Command runner replacing Make | Rust-based, no file-timestamp semantics, clean syntax, `{{var}}` interpolation |
| ruff | >=0.15 | Python linter + formatter | From Astral (same as uv), replaces flake8+black+isort, extremely fast |

### CI Actions
| Action | Version | Purpose |
|--------|---------|---------|
| `extractions/setup-just` | v3 | Install just in CI runner |
| `astral-sh/setup-uv` | v7 | Install uv + Python in CI runner |
| `docker/build-push-action` | v6 | Build+push container (already in use) |
| `docker/metadata-action` | v5 | Tag generation (already in use) |
| `docker/login-action` | v3 | GHCR auth (already in use) |
| `actions/checkout` | v4 | Repo checkout (already in use) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| just | make | Make has file-timestamp semantics that add complexity for pure command-running |
| just | task (go-task) | Task uses YAML; just has more Make-like feel, better for this migration |
| ruff | flake8+black+isort | Three tools vs one; ruff is 10-100x faster |

**Installation (local dev):**
```bash
brew install just        # macOS
uv add --dev ruff        # add ruff to project dev deps
```

## Architecture Patterns

### Justfile Structure
```
# Project constants
IMAGE := "ghcr.io/hellothisisflo/sketchpad"
NS    := "sketchpad"
SHA   := `git rev-parse --short HEAD`
TAG   := "sha-" + SHA

# Default recipe: show available commands
default:
    @just --list

# --- Build ---
recipe-name:
    command here

# --- Dev ---
recipe-name:
    command here

# --- K8s ---
recipe-name:
    command here
```

### Key Justfile Syntax (vs Makefile)

| Make | Just | Notes |
|------|------|-------|
| `VAR := $(shell cmd)` | `` VAR := `cmd` `` | Backtick for shell evaluation |
| `$(VAR)` | `{{VAR}}` | Double-brace interpolation |
| `.PHONY: target` | (not needed) | Just always runs recipes |
| `VAR := value` | `VAR := "value"` | Just uses `:=`, quotes for strings |
| Tab-indented commands | Tab or space (4-space convention) | Just is flexible on indentation |
| `@echo` to suppress | `@` prefix on line or recipe | `@just --list` suppresses the echo |

### CI Pipeline Order (from CONTEXT.md)
```
checkout -> setup-just -> setup-uv -> just test -> just lint -> Docker login -> Docker build+push
```

### Anti-Patterns to Avoid
- **Loading .env for project identity:** IMAGE and NS are constants, not config. Hardcode in Justfile.
- **Stub recipes that don't work:** Every recipe must be functional. No `# TODO` placeholders.
- **Using `make` syntax in Justfile:** `$(shell ...)`, `$@`, `$<` don't exist in just. Use backticks and `{{}}`.
- **Forgetting `@` prefix:** Without it, just echoes every command before running it. Use `@` on `just --list` in default recipe.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container tagging | Manual tag string construction | `docker/metadata-action` | Handles sha, latest, semver, labels automatically |
| CI just installation | curl/wget install script | `extractions/setup-just@v3` | Handles versions, caching, authentication |
| Python env in CI | Manual pip/venv setup | `astral-sh/setup-uv@v7` | Handles uv install, caching, Python version |
| Lint + format | flake8 + black + isort configs | ruff (single tool) | One config, one tool, 10-100x faster |

## Common Pitfalls

### Pitfall 1: Just Variable Interpolation in Shell
**What goes wrong:** `$VAR` in recipe commands refers to shell variables, not just variables. Forgetting `{{}}` causes silent failures.
**How to avoid:** Always use `{{VAR}}` for just variables. Use `$SHELL_VAR` only for actual shell variables.
**Warning signs:** Commands that run but produce wrong output (empty strings).

### Pitfall 2: Ruff Format One-Time Commit Ordering
**What goes wrong:** Adding `just lint` recipe before running the initial format pass means lint will fail on existing unformatted code.
**How to avoid:** Do the one-time `ruff format .` commit BEFORE the `just lint` recipe is expected to work in CI.
**Warning signs:** CI failures on the first push after adding lint gates.

### Pitfall 3: CI Step Ordering -- uv sync Before just test
**What goes wrong:** `just test` calls `uv run pytest` which needs dependencies installed. If `uv sync` hasn't run, pytest/ruff won't be available.
**How to avoid:** Add `uv sync --locked --dev` step between setup-uv and just test. Or rely on `uv run` auto-installing (slower but works).
**Warning signs:** "command not found: pytest" in CI logs.

### Pitfall 4: Docker buildx Platform Flag
**What goes wrong:** The Makefile had `--platform linux/amd64` for local builds targeting K8s. If the Justfile build recipe drops this, local builds may target the wrong arch (arm64 on Apple Silicon).
**How to avoid:** Preserve `--platform linux/amd64` in the build recipe, same as the Makefile.

### Pitfall 5: setup-just Without Version Pin
**What goes wrong:** Using `just-version: '*'` (default) means CI could break on a future just release.
**How to avoid:** Pin to `just-version: '1'` (any 1.x) or a specific version. The `1` pin is safe since just has strong backwards compatibility post-1.0.

## Code Examples

### Complete Justfile Translation

```just
# Sketchpad - Build & Deploy
# Run `just` with no args to see available recipes.

IMAGE := "ghcr.io/hellothisisflo/sketchpad"
NS    := "sketchpad"
SHA   := `git rev-parse --short HEAD`
TAG   := "sha-" + SHA

# Show available recipes
default:
    @just --list

# Build container image (linux/amd64 for K8s)
build:
    docker buildx build --platform linux/amd64 -t {{IMAGE}}:{{TAG}} -t {{IMAGE}}:latest --load .

# Deploy to K8s (assumes image already pushed by CI)
deploy:
    kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Rolling restart
restart:
    kubectl rollout restart deployment/sketchpad -n {{NS}}
    kubectl rollout status deployment/sketchpad -n {{NS}} --timeout=120s

# Show pod and service status
status:
    kubectl get pods -n {{NS}}
    kubectl get svc -n {{NS}}

# Run tests
test:
    uv run pytest

# Lint check
lint:
    uv run ruff check .

# Format code
fmt:
    uv run ruff format .

# Run dev server locally
dev:
    uv run python -m sketchpad

# Tail pod logs
logs:
    kubectl logs -f -l app=sketchpad -n {{NS}} --tail=100
```

### Ruff Configuration in pyproject.toml

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.15"]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "B", "I"]
# E4/E7/E9: pycodestyle errors
# F: pyflakes
# B: flake8-bugbear (common bugs)
# I: isort (import sorting)

[tool.ruff.format]
quote-style = "double"
```

### Updated CI Workflow

```yaml
name: Build and Push Container Image

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: hellothisisflo/sketchpad

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Install just
        uses: extractions/setup-just@v3
        with:
          just-version: '1'

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          python-version: "3.12"
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --dev

      - name: Run tests
        run: just test

      - name: Run linter
        run: just lint

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest
            type=sha,prefix=sha-

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Makefile for command running | Justfile (just) | just 1.0 stable, 2024 | No .PHONY, clean interpolation, cross-platform |
| flake8 + black + isort | ruff (single tool) | ruff 0.1+, 2023-2024 | One config, one tool, dramatically faster |
| Manual CI tool install | Dedicated setup-* actions | 2023+ | Caching, version management, auth handled |

**Deprecated/outdated:**
- `make` for pure command-running: Still works, but `.PHONY`, `$(shell ...)`, and tab-sensitivity are unnecessary complexity
- Separate flake8/black/isort: ruff replaces all three with a single unified tool

## Open Questions

1. **Dev server command**
   - What we know: `python -m sketchpad` starts the server via `__main__.py`
   - What's unclear: Whether env vars (DATA_DIR, etc.) need to be set for local dev
   - Recommendation: Use `uv run python -m sketchpad` -- uv handles the venv. For env vars, user can use a `.env` file manually or set them in shell.

2. **`uv sync` vs `uv run` in CI**
   - What we know: `uv run pytest` auto-installs deps on first run, but `uv sync --locked --dev` is explicit and faster for subsequent commands
   - Recommendation: Use explicit `uv sync --locked --dev` step, then `just test` / `just lint` call `uv run` which finds the already-synced env.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest` |
| Full suite command | `uv run pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUILD-01 | Justfile has all expected recipes | smoke | `just --list` (verify output contains all recipe names) | N/A -- manual verification |
| BUILD-01 | Justfile recipes produce same results as Make | smoke | `just build` / `just status` etc. | N/A -- manual verification |
| BUILD-02 | CI workflow uses setup-just and gates on test+lint | smoke | Push to main and verify CI run | N/A -- manual verification via GitHub Actions |

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (existing tests still pass)
- **Per wave merge:** `uv run pytest -v && uv run ruff check .` (all tests + lint clean)
- **Phase gate:** Full suite green + CI pipeline green on push to main

### Wave 0 Gaps
None -- existing test infrastructure covers regression. BUILD-01/BUILD-02 are tooling changes verified by running the tools themselves (just --list, CI pipeline run), not by pytest tests.

## Sources

### Primary (HIGH confidence)
- [just GitHub repo](https://github.com/casey/just) - syntax, variables, recipes, settings
- [just manual](https://just.systems/man/en/) - official programmer's manual
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/) - pyproject.toml config, rule sets, defaults
- [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/) - CI setup, caching, sync commands
- [extractions/setup-just](https://github.com/extractions/setup-just) - v3, usage, version pinning
- [astral-sh/setup-uv](https://github.com/astral-sh/setup-uv) - v7, Python version, caching

### Secondary (MEDIUM confidence)
- [Justfile cheatsheet](https://cheatography.com/linux-china/cheat-sheets/justfile/) - syntax quick reference
- [just releases](https://github.com/casey/just/releases) - v1.46.0 confirmed as latest (Jan 2, 2026)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools verified via official docs and repos
- Architecture: HIGH - Justfile syntax well-documented, CI pattern follows official guides
- Pitfalls: HIGH - Based on direct Makefile->Justfile syntax differences and CI ordering logic

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable tools, slow-moving domain)
