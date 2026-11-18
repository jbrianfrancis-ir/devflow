## Summary

<!-- What changes and why. -->

## Checks
- [ ] `python3 scripts/validate-plugin.py` passes (JSON manifests + frontmatter)
- [ ] New/changed skills end with a `FLOW:` status line (see `plugins/devflow/references/autonomy.md`)
- [ ] State-file templates keep their size caps; ARCHITECTURE/DESIGN constraints still honored
- [ ] Commands remain `/flow-*`
- [ ] Shipped change (`plugins/devflow/**`) adds one `changes/<slug>.md` fragment (`bump: major|minor|patch`, then the CHANGELOG bullet); manifest versions and `CHANGELOG.md` are **not** edited — only a `release/X.Y.Z` PR made by `scripts/release-cut.py` touches them ([docs/releasing.md](../docs/releasing.md))

## Host smoke receipt

Required when the PR touches `plugins/devflow/**`: proof that the changed plugin loads and runs from this working tree, not the installed copy. Load it for one session only, run one skill on a throwaway fixture (for example `/devflow:flow-status` in an empty temp dir), and paste the key output line. Commands: [`docs/installation.md`](../docs/installation.md#test-the-working-tree-for-one-session).

Every row is filled. A host you could not run is `NOT RUN — <reason>`; a row is never blank or removed.

| Host | Load command (this working tree, one session) | Skill run on fixture | Key output line |
|------|-----------------------------------------------|----------------------|-----------------|
| Claude Code | | | |
| Codex | | | |
| Copilot CLI | | | |
