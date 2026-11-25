bump: patch
`/flow-ci` reads check state with `gh pr view <n> --json statusCheckRollup` instead of `gh pr checks <n> --json …`, which fails on older `gh` (2.46.0: `unknown flag: --json`); a test now blocks `gh pr checks --json` anywhere in plugin content.
