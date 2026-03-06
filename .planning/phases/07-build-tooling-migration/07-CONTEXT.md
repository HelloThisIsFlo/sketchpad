# Phase 7: Build Tooling Migration - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Makefile is replaced by Justfile with equivalent and expanded functionality. CI updated to gate on tests and lint before building. Ruff set up as linter/formatter with a one-time formatting commit. No local container push — CI is the only path to the registry.

</domain>

<decisions>
## Implementation Decisions

### Recipe scope
- Translate all Makefile recipes except `push` and `all` (push is CI-only, all depended on push)
- Kept recipes: `build`, `deploy`, `restart`, `status`
- New dev recipes: `test` (wraps `uv run pytest`), `lint` (wraps `uv run ruff check`), `fmt` (wraps `uv run ruff format`), `dev` (local dev server), `logs` (kubectl logs -f)
- Only include recipes that actually work and are useful — no stubs

### No local push
- Remove `push` recipe entirely — CI is the only path to the container registry
- Remove `all` recipe (was `build push deploy`) — no longer makes sense without push
- Deploy recipe assumes CI has already pushed the image

### CI integration
- Keep Docker GitHub Actions (`docker/build-push-action`, `docker/metadata-action`) for container build+push — they handle tagging, labels, and registry auth natively
- Add `setup-just` action to CI workflow
- Add `just test` and `just lint` steps that must pass before Docker build+push runs (gate on both)
- CI runs: checkout → setup-just → setup-python/uv → just test → just lint → Docker login → Docker build+push

### Ruff setup
- Add ruff as dev dependency in pyproject.toml
- Basic ruff config in pyproject.toml (sensible defaults)
- One-time formatting commit to normalize all existing code before adding lint/format recipes
- `just lint` and `just fmt` wrap ruff commands

### Just conventions
- Hardcode project constants in Justfile (IMAGE, NS) — not .env (these are identity, not config)
- Default recipe (`just` with no args) shows `just --list` — safe and discoverable
- Lowercase recipe names with hyphens for multi-word (e.g., `run-dev`)
- Backtick expressions for shell commands (e.g., `` SHA := `git rev-parse --short HEAD` ``) — cleaner than Make's `$(shell ...)`
- No `.PHONY` needed — Just recipes always run (not file-based targets)

### Claude's Discretion
- Exact ruff rule configuration (sensible defaults for a small Python project)
- Deploy recipe adjustments (now that push is CI-only)
- Dev server recipe implementation (local server start command)
- Logs recipe flags (follow, tail count, etc.)
- Whether to keep the `build` recipe for local Docker testing or simplify it

</decisions>

<specifics>
## Specific Ideas

- User's first time using Justfile — conventions should be idiomatic and discoverable
- User was already thinking about removing local push before this phase — CI-only publishing was a pre-existing preference
- Ruff formatting should be a one-time commit that normalizes everything, so future diffs are clean

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Makefile`: 6 recipes (build, push, deploy, restart, all, status) — 4 translate directly, 2 removed
- `.github/workflows/build.yaml`: Docker GitHub Actions pipeline — kept, extended with Just steps
- `pyproject.toml`: Build config with pytest — add ruff dev dependency and config here

### Established Patterns
- Environment-based config via `get_config()` with `@lru_cache` (app config, not build config)
- Docker buildx with `--platform linux/amd64` for local builds (K8s target is amd64)
- Namespace `sketchpad` for all K8s resources

### Integration Points
- `Makefile` → deleted after Justfile verified
- `.github/workflows/build.yaml` → add setup-just, setup-python/uv, test+lint gates
- `pyproject.toml` → add ruff to dev dependencies, add `[tool.ruff]` config
- All Python source files → one-time ruff format pass

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-build-tooling-migration*
*Context gathered: 2026-03-06*
