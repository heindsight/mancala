# Two rulesets on `main`, and Renovate-side automerge

Renovate merges its own dependency PRs. So `main` must let the bot skip the
review requirement, but nothing else. To do that, `main` has two rulesets
instead of one:

- **Review** — the `pull_request` rule. Its bypass list holds the repo-admin
  role and `renovate[bot]`, with `bypass_mode: pull_request`.
- **Checks** — the required status checks, code scanning, code quality, code
  coverage, and the `creation`, `deletion` and `non_fast_forward` rules. Its
  bypass list is empty.

Renovate does the merging (`platformAutomerge: false`). It reads the check
results, and on its next run after they pass, it merges the PR through the API.
Renovate is a bypass actor on Review, so the review rule does not block that
merge. Nobody can bypass Checks, so GitHub still refuses to merge a PR with a
failing required check.

## Considered options

**One ruleset.** That is what `main` had. A bypass actor skips the whole
ruleset, not one rule inside it. So putting `renovate[bot]` on a ruleset that
holds both the review rule and the checks would let its PRs merge before CI ran.

**Branch rules in the Review ruleset.** Renovate can bypass Review. Its bypass
mode already stops it from deleting or force-pushing `main`, but keeping those
rules in Checks means nobody can bypass them at all.

**GitHub-side automerge (`platformAutomerge: true`).** Renovate turns on
GitHub's own auto-merge, and GitHub merges when the checks pass. That would be
faster, but it does not work with a review bypass. GitHub's auto-merge waits
until every merge requirement is met. It does not use the bypass rights of the
actor that turned it on. PR #19 showed this: every check passed, and the PR
stayed blocked on the review requirement.

## Consequences

A bot PR merges at Renovate's next run after its checks pass, not as soon as
the last check finishes.

GitHub blocks a bot merge only for the checks on the Checks ruleset's required
list: `checks (3.13)`, `checks (3.14)`, `zizmor`, and
`renovate-config-validator`. Renovate also waits for the other checks it can
see, but GitHub does not enforce those.
