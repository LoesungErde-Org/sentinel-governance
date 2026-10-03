# Repository Governance Policy (GitHub)

## Status
Approved

## Scope
This policy defines mandatory repository controls for detection engineering, governance artifacts, rollback workflows, and audit evidence in this repository.

## Protected Branches
- `main`
- `codex/compliance-engine`

## Branch Protection: `main`

### Pull Request Controls (Required)
- Require a pull request before merging: enabled
- Required approvals: 1 minimum
- Require review from CODEOWNERS: enabled
- Dismiss stale approvals when new commits are pushed: enabled
- Require conversation resolution before merging: enabled

### CI Gate Controls (Required)
- Require status checks to pass before merging: enabled
- Require branches to be up to date before merging: enabled
- Required checks:
  - `rollback-smoke`
  - `forecast-schema-validation`
  - `detection-validation`
  - `risk-gate`
  - `governance-guard`

### Integrity Controls (Required)
- Require signed commits: enabled
- Require linear history: enabled
- Allow force pushes: disabled
- Allow deletions: disabled
- Allow bypassing branch protections: disabled

### Hardening Controls (Recommended)
- Lock branch: enabled for governance-critical phases

## Branch Protection: `codex/compliance-engine`

### Merge and Mutation Controls (Required)
- Require a pull request before merging: enabled
- Allow direct pushes: disabled
- Allow force pushes: disabled
- Allow deletions: disabled

### Optional Controls
- Require status checks: optional for iteration speed
- Require signed commits: optional (recommended if team enforces org-wide signing)

## CODEOWNERS Requirement
A `CODEOWNERS` file must define owners for at least:
- `.github/workflows/*`
- `governance/**`
- `tools/**`
- `detections/**`

## Change Management Rules
Any change affecting the following requires explicit "Governance impact" notes in the PR description:
- signature generation or verification
- risk gating thresholds or logic
- rollback resolver/executor behavior
- manifest/signature index structure
- required CI checks

## Audit Mapping
This policy supports:
- deterministic release evidence
- controlled change approvals
- non-bypassable quality and risk gates
- traceable rollback and integrity controls

## Review Cadence
- Quarterly policy review
- Immediate review after any CI workflow rename, gate change, or branch model change

## Activation and deployment evidence

The approved policy above is a requirement, not evidence that remote settings are active.
`branch-quality-policy.json` is the additive default-branch ruleset payload. It must be
merged with green CI before an administrator runs `python tools/apply_branch_policy.py --apply`.
The default command prints the payload and performs no remote writes. Existing rulesets,
including all-branch deletion and force-push controls, are preserved. GitHub plan support
and repository administration permission are prerequisites; private repositories may need
a supported paid plan. Each other repository needs its own verified check names and owners.

Detection, forecast, risk, source-policy and rollback checks run on every main PR.
Dependent gate jobs run with `always()` and fail if their producer did not succeed.
Actions are pinned to full commit SHAs, checkout does not retain credentials, and only
the signing producer and explicitly requested Azure deployment receive OIDC write access.
Cosign v2.6.5 retains the certificate/signature format consumed by rollback verification.

Production deployment is an explicit main-branch `workflow_dispatch` with `deploy=true`.
Configure the `sentinel-production` environment with required reviewers and only main
as an allowed deployment branch before using it. Configure environment variables
`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`,
and `SENTINEL_WORKSPACE`, and an Azure federated credential bound to that environment.
Use an existing Sentinel-enabled workspace and least-privilege Azure role assignment.
Missing variables stop the job before login. No Azure credentials are stored in workflow YAML.

The compiler builds ARM templates only for actual production variants (identity/network).
It preserves stable rule IDs, query thresholds, function aliases, and the experimental
incident prohibition. The query already applies the per-entity threshold, so the Azure
trigger fires on more than zero returned rows. Endpoint/cloud are not deployment targets
until real compiler bindings and functions exist. Templates and their checksum manifest
are included in the keyless-signed rollback snapshot. Deployment downloads this run's
artifact ID, verifies the snapshot signature and template hashes, then validates and
previews every pack before applying any. Azure resource validation remains a live
deployment prerequisite; local JSON tests do not prove KQL validity against production data.

## Exception Handling
Exceptions must be time-bound and documented in a PR with:
- reason
- risk assessment
- compensating controls
- expiry date
- approver
