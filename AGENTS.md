# AGENTS.md

## Purpose
`py-trinnov-altitude` is the protocol and normalization library used by the Home Assistant integration.

## Workflow
- Use `uv` for local commands.
- Run repo-local lint and tests before pushing.
- Keep parsing tolerant and semantics deterministic.

## Design Expectations
- Protocol quirks belong here, not in the Home Assistant layer.
- Preserve stable identifiers and lifecycle semantics across reconnects and cold starts.
- Prefer id-first normalization with graceful fallback labels.

## Commits
- Use conventional commits for releasable changes: `fix: ...` or `feat: ...`.

## Releases
1. Merge normal conventional commits to `master`.
2. Let `release-please` open or update the release PR.
3. Do not manually edit version files or changelogs outside the Release Please PR.
4. Do not manually create tags or GitHub releases.
5. Merge the Release Please PR to publish.
