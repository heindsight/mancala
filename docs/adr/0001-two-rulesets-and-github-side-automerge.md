# Two rulesets on `main`, and GitHub-side automerge for Renovate

Renovate merges its own dependency PRs. So `main` must let the bot skip the
review requirement, but nothing else. To do that, `main` has two rulesets
instead of one:

- **Review** — the `pull_request` rule. Its bypass list holds the repo-admin
  role and `renovate[bot]`, with `bypass_mode: pull_request`.
- **Checks** — the required status checks, code scanning (CodeQL only), code
  quality, code coverage, and the `creation`, `deletion` and `non_fast_forward`
  rules. Its bypass list is empty.

Renovate does not do the merging. It turns on GitHub's own auto-merge
(`platformAutomerge`), and GitHub merges when the checks pass. GitHub's
auto-merge uses Renovate's bypass for the review rule. While it waits, the PR
still shows "review required", so check the ruleset's rule insights to see what
is really blocking a merge.

## Considered options

**One ruleset.** That is what `main` had. A bypass actor skips the whole
ruleset, not one rule inside it. So putting `renovate[bot]` on a ruleset that
holds both the review rule and the checks would let its PRs merge before CI ran.

**Branch rules in the Review ruleset.** Renovate can bypass Review. Its bypass
mode already stops it from deleting or force-pushing `main`, but keeping those
rules in Checks means nobody can bypass them at all.

**Renovate-side automerge.** Renovate reads the check results itself and merges
on its next run. Use that when the checks are not required, because then nothing
else reads them. Here the Checks ruleset requires them and nobody can bypass it,
so GitHub already refuses to merge a failing PR. Letting GitHub merge is also
faster: it happens when the last check finishes, not at the next Renovate run.

**zizmor in the code scanning rule.** zizmor-action uploads its results
against the PR's test merge commit. GitHub builds a new test merge commit when
someone tries to merge, so the rule never found zizmor results and blocked
every merge. Instead, the `zizmor` job runs with `advanced-security: false`.
It then fails when zizmor finds a problem, and it is a required check.

## Consequences

Nothing requires a PR to be up to date with `main`: the required status checks
rule is not strict. That is what makes a batch of Renovate PRs able to land
together. Renovate's default `rebaseWhen` undid it — with automerge on it
rebases any PR that falls behind `main`, so every merge reset the checks on
every other open PR, and the batch drained one PR per Renovate run. The config
sets `rebaseWhen: "conflicted"` instead, so a PR is rebased only when it
actually conflicts. The cost is that a PR merges on checks that ran against an
older `main`; the CI run on `main` after the merge is what catches that.

A check blocks a bot merge only if it is on the Checks ruleset's required list:
`checks (3.13)`, `checks (3.14)`, `zizmor`, and `renovate-config-validator`. A
job that runs but is not required will not stop an automerge.
