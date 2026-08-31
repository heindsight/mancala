# Two rulesets on `main`, and GitHub-side automerge for Renovate

Renovate merges its own dependency PRs, so `main` has to let a bot past the
review requirement without letting it past anything else. `main` is therefore
guarded by two rulesets: a **Review** ruleset carrying the `pull_request` rule,
whose bypass list holds the repo-admin role and `renovate[bot]` with
`bypass_mode: pull_request`, and a **Gates** ruleset carrying the required
status checks, code scanning, code quality and code coverage, whose bypass list
is empty. Renovate merges through `platformAutomerge`, so GitHub merges the PR
once the gates go green.

## Considered options

**One ruleset.** That is what `main` had. A bypass actor is exempted from a
whole ruleset, not from one rule inside it, so adding `renovate[bot]` to a
ruleset that bundles review with the gates would let its PRs merge before CI
had run.

**Renovate-side automerge**, where Renovate reads the check results itself and
merges on its next run. That is the right choice for a repo whose checks are
not required, because then nothing else is reading them. Here the gates ruleset
requires them and its bypass list is empty, so GitHub already refuses to merge
a red PR, and letting GitHub merge is faster: it happens when the last check
finishes, rather than at the next Renovate run.

## Consequences

A gate only blocks a bot merge if it is on the gates ruleset's required-checks
list: `checks (3.13)`, `checks (3.14)`, `zizmor`, and
`renovate-config-validator`. A job that runs but is not required will not stop
an automerge.
