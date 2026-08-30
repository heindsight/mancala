#!/usr/bin/env bash
#
# Repins every agent-workflows reusable-workflow call in this repo to a commit
# SHA, keeping the human-readable ref in a trailing comment:
#
#   uses: heindsight/agent-workflows/.github/workflows/triage.yml@<sha>  # v1
#
# Why: a tag is mutable. Anyone with write access to the config repo can move
# `v1` onto a different commit, and every consumer silently follows it into a job
# holding `contents: write`. A SHA is the only ref that cannot be moved under
# you. Third-party actions in these workflows are already pinned this way; the
# reusable-workflow calls are the last unpinned refs, and the ones that matter
# most, since they are the workflows themselves rather than a step inside one.
#
# The cost: moving the `v1` tag no longer updates consumers. Re-run this after
# each config-repo release — or let Renovate do it, which is what the trailing
# `# v1` comment is for; Renovate reads it to know which tag the SHA tracks.
#
# Idempotent. Run from the root of a consuming repo.

set -euo pipefail

CONFIG_REPO=${CONFIG_REPO:-heindsight/agent-workflows}
REF=${1:-v1}

if ! sha=$(gh api "repos/$CONFIG_REPO/commits/$REF" --jq '.sha' 2>/dev/null); then
  echo "Cannot resolve $CONFIG_REPO@$REF — does the repo exist and is the tag pushed?" >&2
  exit 1
fi
echo "$CONFIG_REPO@$REF -> $sha"

# Matches both an unpinned `@v1` and an already-pinned `@<sha>  # v1`, so a
# re-run after moving the tag rewrites cleanly rather than stacking comments.
pattern="s|(uses: ${CONFIG_REPO}/\.github/workflows/[A-Za-z0-9._-]+\.yml)@[^[:space:]]+[[:space:]]*(#.*)?\$|\1@${sha}  # ${REF}|"

changed=0
for f in .github/workflows/*.yml; do
  [ -e "$f" ] || continue
  before=$(cat "$f")
  after=$(printf '%s\n' "$before" | sed -E "$pattern")
  if [ "$before" != "$after" ]; then
    printf '%s\n' "$after" > "$f"
    echo "  pinned $f"
    changed=$((changed + 1))
  fi
done

if [ "$changed" -eq 0 ]; then
  echo "Nothing to change; already pinned to $sha."
else
  echo "$changed file(s) repinned. Commit them."
fi
