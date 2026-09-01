# Two rulesets on `main`, and GitHub-side automerge for Renovate

Renovate merges its own dependency PRs. So `main` must let the bot skip the
review requirement, but nothing else. To do that, `main` has two rulesets
instead of one:

- **Review** — the `pull_request` rule. Its bypass list holds the repo-admin
  role and `renovate[bot]`, with `bypass_mode: pull_request`.
- **Checks** — the required status checks, code scanning, code quality and code
  coverage. Its bypass list is empty.

Renovate does not do the merging. It turns on GitHub's own auto-merge
(`platformAutomerge`), and GitHub merges when the checks pass.

## Considered options

**One ruleset.** That is what `main` had. A bypass actor skips the whole
ruleset, not one rule inside it. So putting `renovate[bot]` on a ruleset that
holds both the review rule and the checks would let its PRs merge before CI ran.

**Renovate-side automerge.** Renovate reads the check results itself and merges
on its next run. Use that when the checks are not required, because then nothing
else reads them. Here the Checks ruleset requires them and nobody can bypass it,
so GitHub already refuses to merge a failing PR. Letting GitHub merge is also
faster: it happens when the last check finishes, not at the next Renovate run.

## Consequences

A check blocks a bot merge only if it is on the Checks ruleset's required list:
`checks (3.13)`, `checks (3.14)`, `zizmor`, and `renovate-config-validator`. A
job that runs but is not required will not stop an automerge.
