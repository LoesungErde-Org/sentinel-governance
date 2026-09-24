# Quarterly Governance Review Cycle

## Purpose
Defines the recurring quarterly review process for evaluating governance performance, control effectiveness, maturity progression, and audit readiness within the SENTINEL repository.

## Review Cadence
- Frequency: Quarterly (Q1, Q2, Q3, Q4)
- Duration: 60-90 minutes
- Review window: first 15 business days of each quarter
- Participants:
  - Governance Owner
  - CAB Representative
  - Security/Compliance Lead
  - Engineering Lead (optional)
  - Audit Liaison (optional)

## Inputs (Pre-Read Package)
Required inputs for each quarterly review:
- Governance KPIs and SLOs for previous quarter
- Evidence matrix deltas
- Governance integrity test suite results
- Governance drift incidents or alerts (if any)
- Policy change-control log
- PRs touching governed paths
- Release checklist outcomes
- Maturity rubric self-assessment

## Agenda (Structured)
1. Opening and scope confirmation
2. Review of governance KPIs and SLOs
3. Evidence flow evaluation
4. Integrity suite findings and trend
5. Governance drift analysis
6. Policy change-control review
7. Maturity rubric progression
8. Risks, exceptions, and compensating controls
9. Decisions and approvals
10. Action items, owners, and due dates
11. Evidence packaging for audit

## KPI and SLO Evaluation
Minimum KPI set:
- KPI 1: Governance PR approval compliance
- KPI 2: Governance integrity suite pass rate
- KPI 3: Evidence matrix completeness
- KPI 4: Governance drift incidents
- KPI 5: Policy change-control SLA adherence

Minimum SLO set:
- SLO 1: Review turnaround time
- SLO 2: Evidence packaging latency
- SLO 3: CAB decision SLA

## Decision Log (Quarterly)
| Decision | Owner | Rationale | Effective Date | Evidence |
|---|---|---|---|---|
| | | | | |

## Action Tracking
| Action Item | Owner | Due Date | Status | Evidence |
|---|---|---|---|---|
| | | | | |

## Audit Evidence Output
Each quarterly review must produce:
- Signed review summary
- KPI and SLO evaluation sheet
- Updated evidence matrix (if changed)
- Quarterly decision log
- Action tracking sheet
- Governance maturity delta
- CAB approvals (if triggered)

Storage convention:
- `governance/evidence/quarterly/YYYY-QX/`

Minimum files:
- `review-summary.md`
- `kpi-slo-evaluation.json`
- `decision-log.md`
- `action-tracking.md`
- `maturity-delta.md`

## Roles and Accountability
- Governance Owner: chairs review and confirms closure criteria
- CAB Representative: confirms CAB-linked decisions and escalations
- Compliance Lead: validates evidence quality and control mapping
- Engineering Lead: confirms operational feasibility and deadlines

## Closure Criteria
A quarterly review is complete only when:
- Decision log is finalized
- Actions have owners and due dates
- Evidence package is stored in quarterly path
- Deviations and exceptions are documented

## Escalation Rules
Escalate to CAB when one or more are true:
- Critical governance control failed in production branch flow
- Repeated governance drift over two consecutive review cycles
- Missing or unverifiable evidence for required controls
- Any change that weakens branch protection or integrity controls

## Versioning and Change-Control
This document is governed by:
- `governance/policy-change-control.md`
- `.github/workflows/governance-guard.yml`
- `.github/workflows/governance-integrity.yml`
