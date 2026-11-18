# Releasing

Feature PRs never edit the version. Each one that changes `plugins/devflow/**` adds one fragment, `changes/<slug>.md`:

```
bump: minor
The CHANGELOG bullet for this change.
```

The `bump:` line (`major`, `minor` or `patch`) may also sit in `---` front matter. Parallel PRs then touch different files, so they no longer conflict on the three manifest `version` lines or the CHANGELOG top entry.

`scripts/check-change-fragment.py` (lint.yml, PRs only) fails a PR that ships plugin content with no new fragment, a fragment without a valid `bump:` line, or a non-release PR that edits a manifest `version` line or `CHANGELOG.md`.

To release: run `python3 scripts/release-cut.py --dry-run` to preview, then without `--dry-run`. It takes the highest bump across all fragments, writes the next version to `plugins/devflow/.claude-plugin/plugin.json`, `plugins/devflow/.codex-plugin/plugin.json` and `.claude-plugin/marketplace.json`, prepends one `## X.Y.Z (YYYY-MM-DD)` CHANGELOG entry from the fragment bullets, and deletes the fragments. Commit that on a `release/X.Y.Z` branch and open a PR. `main` is branch-protected and Actions cannot push to it, so the release is this small PR; once it merges, `release.yml` sees a new plugin.json version and tags it.
