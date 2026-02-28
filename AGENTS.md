# AGENTS.md

## Purpose
`py-trinnov-altitude` is the protocol/library layer. Home Assistant integration depends on this package.

## Development Workflow
- Use `uv` for all local tasks.
- Key commands:
  - `uv sync --group dev`
  - `uv run ruff check trinnov_altitude tests`
  - `uv run ruff format trinnov_altitude tests`
  - `uv run pytest -q`
- Real-device read-only smoke tests:
  - Configure `.env` with `TRINNOV_HOST=<ip>`
  - `set -a && source .env && set +a && TRINNOV_ITEST=1 uv run pytest -q -m integration_real`

## Protocol Architecture Expectations
- Keep parser broad/tolerant (raw message decoding only).
- Keep semantics in normalization (quirk profiles).
- Keep state reducer id-first and deterministic.
- Current quirk profile behavior:
  - `altitude_ci` selected via `IDENTS` feature set.
  - `META_PRESET_LOADED` normalizes to source-change in `altitude_ci`, preset-change otherwise.

## Commit Conventions
- Use conventional commits for releasable changes:
  - `fix: ...` or `feat: ...`
- Non-conventional commit messages will be ignored by release-please for version bumps.

## Release Process
1. Push conventional commits to `master`.
2. `release-please` workflow runs on push.
3. Important repo nuance:
   - GitHub Actions here can update `release-please--branches--master` but cannot create PRs.
   - Manually create release PR:
     - `gh pr create --base master --head release-please--branches--master --title 'chore(master): release X.Y.Z' --body '...'
4. Wait for CI checks on release PR.
5. Merge release PR (repo policy may require admin and disallow merge commits).
6. Ensure GitHub Release tag exists (if not auto-created, create manually):
   - `gh release create vX.Y.Z --target master --title 'vX.Y.Z' --notes '...'
7. Verify publish workflow success (`publish.yml`) and PyPI release availability.

## Branch Protection / Merge Mechanics
- Direct pushes may be possible via bypass, but normal expectation is PR flow.
- Merge strategy constraints can reject `--merge`; use allowed mode (`--squash` or `--rebase`) with `--admin` when needed.

## Cross-Repo Coordination
- Release library first.
- Then bump minimum required version in `trinnov-altitude-homeassistant` and release integration.

## Session Hygiene
- Before starting release work, check:
  - `gh run list --limit 10`
  - `gh pr list --state open --limit 20`
  - `gh release list --limit 10`
- Before pushing, always run lint + tests locally.
