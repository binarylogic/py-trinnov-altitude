# Maintainer Runbook

## Branch protection (recommended)

Apply to `master`:

- Require pull request before merging
- Require approvals: `1`
- Dismiss stale approvals on new commits
- Require status checks to pass before merging
- Required checks:
  - `CI`
- Require branches to be up to date before merging
- Restrict force pushes and branch deletion

## Dependency management

Dependabot is configured for:

- GitHub Actions (weekly)
- Python dependencies from `pyproject.toml` (weekly)

## Release procedure

1. Ensure `master` is green.
2. Merge conventional commits to `master` (feat/fix/breaking).
3. Wait for `release-please` to open or update the release PR.
4. Review and merge the release PR.
5. Confirm the generated GitHub Release triggered the `Release` publish workflow.
6. Optionally run `Release` manually with `target=testpypi` for staged validation.

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
3. Merge the next release-please PR to publish `vX.Y.(Z+1)`.
