# Releasing

Releases happen on merge. Nobody cuts one by hand, and no PR edits a version.

Each PR that changes `plugins/devflow/**` adds one fragment, `changes/<slug>.md`:

```
bump: minor
The release-note bullet for this change.
```

The `bump:` line (`major`, `minor` or `patch`) may also sit in `---` front matter. Parallel PRs touch different files, so they do not conflict.

On every push to `main`, `.github/workflows/release.yml` runs `scripts/next-release.py`. It takes the highest `vX.Y.Z` tag merged into `main` (0.57.0 if there is none) and bumps it by the highest `bump:` among the fragments added since that tag (`git diff --diff-filter=A <tag>..HEAD -- changes/`). It then creates the tag and a GitHub Release whose notes are those fragments' bullets, followed by GitHub's generated PR list. No fragment added since the tag means no release. Nothing is committed back, so branch protection on `main` is untouched. Fragments are never deleted; they stay as history. `python3 scripts/next-release.py` previews the next release locally, and `lint.yml` prints the same preview on every PR. To retry a failed run, use **Run workflow** on `release.yml`.

The manifests carry no `version`. A committed version pins every install to it until someone changes it ([Claude Code: Versions and updates](https://code.claude.com/docs/en/plugins/loading.md#versions-and-updates)). Without one, Claude Code uses the commit SHA of the plugin directory, so installs follow `main`. Codex caches a `local`-source plugin as `local` and does not use the version to decide updates.

`scripts/validate-plugin.py` fails if any manifest sets `version`. `scripts/check-change-fragment.py` (`lint.yml`, PRs only) fails a PR in three cases: it ships plugin content with no new fragment; a fragment has no valid `bump:` line; or it adds a manifest `version` line or edits a released `CHANGELOG.md` entry. `CHANGELOG.md` holds the history up to 0.57.0, and from 0.58.0 on releases are recorded in [GitHub Releases](https://github.com/jbrianfrancis-ir/devflow/releases).
