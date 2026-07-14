## Summary

<!-- What changes and why. -->

## Checks
- [ ] `python3 scripts/validate-plugin.py` passes (JSON manifests + frontmatter)
- [ ] New/changed skills end with a `FLOW:` status line (see `references/autonomy.md`)
- [ ] State-file templates keep their size caps; ARCHITECTURE/DESIGN constraints still honored
- [ ] Commands remain `/flow-*`
- [ ] `version` bumped in `.claude-plugin/plugin.json` + `marketplace.json` if behavior changed (the version string is the update cache key — no bump means installed copies never see the change)
