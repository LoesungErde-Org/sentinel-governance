# Detection Engineering Platform Scaffold

This repository includes the structural baseline for large-scale Sentinel detection engineering.

## Implemented additions
- Detection packs by domain in `detections/*`
- Release versioning in `releases/*/manifest.json`
- Ownership metadata schema in `docs/detection-rule.schema.json`
- Automatic tuning suggestions via `tools/generate_tuning_suggestions.py`
- MITRE technique template library starter in `templates/mitre-techniques`
- Coverage heatmap generation in `tools/generate_coverage_heatmap*.py`
- Release manifest automation in `tools/update_manifest.py`
- Rule compiler with variant matrix in `tools/rule_compiler.py`
- Snapshot hook for baseline evidence in `tools/snapshot_hook.py`
- Forecast hook + schema in `tools/forecast_hook.py` and `tools/forecast.schema.json`
- CAB markdown renderer in `tools/render_cab_report.py`
- CI risk gate in `tools/risk_gate.py`
- Keyless signature verification in `tools/verify_signatures.py`
- Signature index generation in `tools/generate_signature_index.py`
- Snapshot rollback resolver and restore scripts in `tools/resolve_snapshot_entry.py` and `tools/rollback_from_snapshot.py`
- CI pipeline in `.github/workflows/detections-ci.yml`
- Rollback pipeline in `.github/workflows/rollback.yml`

## Quick start
```powershell
python tools/expand_mitre_templates.py --input templates/mitre-techniques --output detections
python tools/rule_compiler.py --template templates/mitre-techniques/T1110-password-spray.compiler.json --params tools/rule_params.example.yaml --repo . --snapshot --forecast --compiled-output governance/compiled-rules.json
python tools/validate_detection_rules.py --path detections
python tools/validate_json.py --schema tools/forecast.schema.json --input governance/forecast.json
python tools/render_cab_report.py --forecast governance/forecast.json --output governance/cab-report.md
python tools/risk_gate.py --forecast governance/forecast.json --fail-on-block
python tools/update_manifest.py --rules detections --output releases/current/manifest.json --release current
```

## Keyless Signing (Sigstore/Cosign + GitHub OIDC)
- Workflow permissions: `id-token: write`, `contents: write`
- Signed artifacts: `governance/forecast.json`, `governance/baselines/detection-snapshot.json`, `governance/compiled-rules.json`, `governance/cab-report.md`, `governance/snapshots/current/snapshot.tar.gz`
- Signature outputs: `governance/signatures/*.sig`, `governance/signatures/*.pem`, `governance/signatures/*.sha256`, `governance/signatures/index.json`
- Gate: `tools/verify_signatures.py` validates issuer `https://token.actions.githubusercontent.com` and workflow identity from `${{ github.workflow_ref }}`

## Rollback
- Workflow: `.github/workflows/rollback.yml`
- Snapshot resolver: `tools/resolve_snapshot_entry.py`
- Restore script: `tools/rollback_from_snapshot.py`
- CAB template: `governance/templates/cab-comment-template.md`
- Oncall runbook: `docs/runbooks/soc-oncall-rollback.md`

## Forecast Operations
- Forecast build checklist (On-Call): `docs/runbooks/forecast-build-checklist.md`

## Rollback Tests
- Unit tests: `python -m pytest -q tests/test_rollback.py`
- CI smoke workflow: `.github/workflows/rollback-smoke.yml`
\n- Mid-swap failure test: python -m pytest -q tests/test_rollback_mid_swap.py\n
