# Maintainer Runbook

## Branch protection (recommended)

Apply to `master`:

- Require pull request before merging
- Require approvals: `1`
- Dismiss stale approvals on new commits
- Require status checks to pass before merging
- Required checks:
  - `Quality (3.13)`
  - `Tests (Python 3.10)`
  - `Tests (Python 3.11)`
  - `Tests (Python 3.12)`
  - `Tests (Python 3.13)`
  - `Package build check`
- Require branches to be up to date before merging
- Restrict force pushes and branch deletion

## Dependency management

Dependabot is configured for:

- GitHub Actions (weekly)
- Python dependencies from `pyproject.toml` (weekly)

## Release procedure

1. Ensure `master` is green.
2. Bump `__version__` in `trinnov_altitude/__init__.py`.
3. Update `CHANGELOG.md`.
4. Commit and merge.
5. Create prerelease tag `vX.Y.ZrcN` to publish to TestPyPI.
6. Validate install from TestPyPI.
7. Create release tag `vX.Y.Z` to publish to PyPI.

### Optional Pyx publish

If you also need a Pyx release, run `Release` via `workflow_dispatch` with
`target=pyx`.

Required repository secrets:

- `PYX_API_KEY`
- `PYX_PUBLISH_URL` (Pyx upload endpoint, e.g. `https://api.pyx.dev/v1/upload/<org>/<workspace>`)

## Emergency rollback

If bad release is published:

1. Yank the PyPI release version.
2. Create patch fix on `master`.
3. Cut new release `vX.Y.(Z+1)`.
