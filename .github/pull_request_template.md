## Summary

<!-- What changes and why. -->

## Checks
- [ ] `python3 scripts/validate-plugin.py` passes (JSON manifests + frontmatter)
- [ ] New/changed skills end with a `FLOW:` status line (see `plugins/devflow/references/autonomy.md`)
- [ ] State-file templates keep their size caps; ARCHITECTURE/DESIGN constraints still honored
- [ ] Commands remain `/flow-*`
- [ ] `version` bumped in **all three** manifests if behavior changed — `plugins/devflow/.claude-plugin/plugin.json`, `plugins/devflow/.codex-plugin/plugin.json`, and `.claude-plugin/marketplace.json` (the validator enforces that they match; the version string is the update cache key — no bump means installed copies never see the change)
