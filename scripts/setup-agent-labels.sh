#!/usr/bin/env bash
#
# Creates the labels the agent workflows read. Idempotent.
#
# The five triage labels are the ONLY ones the triage pipeline may apply.
# `ready-for-agent` is deliberately outside that set: it is the gate between the
# untrusted triage path and the implement runner, and only you apply it.

set -euo pipefail
REPO=${1:-heindsight/mancala}

label() {  # name colour description
  gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force
}

# Triage vocabulary (docs/agents/triage-labels.md)
label needs-triage    "d876e3" "Maintainer needs to evaluate this issue"
label needs-info      "fbca04" "Waiting on reporter for more information"
label ready-for-human "0e8a16" "Requires human implementation"
label wontfix         "ffffff" "Will not be actioned"
label not-actionable  "cfd3d7" "Not a unit of work: bot dashboard, status board or notification"

# The approval gate — applied by hand, never by an agent
label ready-for-agent "5319e7" "Reviewed and approved for the unattended agent runner"

# Per-issue overrides for the implement runner
label agent:model:opus    "1d76db" "Run this ticket on Opus"
label agent:model:sonnet  "1d76db" "Run this ticket on Sonnet"
label agent:effort:low    "c5def5" "Low reasoning effort"
label agent:effort:medium "c5def5" "Medium reasoning effort"
label agent:effort:high   "c5def5" "High reasoning effort"

echo "Labels ready on $REPO."
