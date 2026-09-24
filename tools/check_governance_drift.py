#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

# --------------------------------------------------------------------
# Normalization helpers
# --------------------------------------------------------------------

def normalize_pattern(p: str) -> str:
    """Normalize CODEOWNERS patterns by removing leading slashes and trimming whitespace."""
    return p.strip().lstrip('/')


# Required rules in documented form (no leading slash)
REQUIRED_RULES = [
    '.github/workflows/*',
    'governance/**',
    'tools/**',
    'detections/**',
]

# Core governance artifacts that must exist
CORE_REQUIRED_FILES = [
    '.github/CODEOWNERS',
    'governance/repository-governance.md',
]


# --------------------------------------------------------------------
# Report builders
# --------------------------------------------------------------------

def build_recommendations(drift_items: list[dict]) -> list[str]:
    """Generate recommendations based on drift items."""
    recs: list[str] = []
    for drift in drift_items:
        rule = drift.get('rule', '')
        if rule == 'CODEOWNERS_presence':
            recs.append('Add a .github/CODEOWNERS file to satisfy core governance requirements.')
        elif rule in REQUIRED_RULES:
            recs.append(f'Add required CODEOWNERS rule: {rule}')
        else:
            recs.append(f"Review drift: {drift.get('message', 'Unknown drift detected.')}")
    return recs


def build_report(drift_items: list[dict]) -> dict:
    """Build a unified drift report structure."""
    return {
        'drift': drift_items,
        'recommendations': build_recommendations(drift_items),
    }


def write_report(report: dict, json_out: Path, md_out: Path) -> None:
    """Write JSON and Markdown outputs."""
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        lines = ['# Drift Report', '']
        for drift in report['drift']:
            lines.append(f"- **{drift['severity']}** — {drift['rule']}: {drift['message']}")
        lines.append('')
        lines.append('## Recommendations')
        for recommendation in report['recommendations']:
            lines.append(f'- {recommendation}')
        md_out.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# --------------------------------------------------------------------
# Main drift checker
# --------------------------------------------------------------------

def check_governance_drift(repo_path: Path, json_out: Path, md_out: Path) -> int:
    if not json_out.is_absolute():
        json_out = repo_path / json_out
    if not md_out.is_absolute():
        md_out = repo_path / md_out

    drift_items: list[dict] = []

    # ----------------------------------------------------------------
    # Check core required artifacts
    # ----------------------------------------------------------------
    for core_file in CORE_REQUIRED_FILES:
        path = repo_path / core_file
        if not path.is_file():
            drift_items.append({
                'severity': 'high',
                'rule': core_file,
                'message': f'Required core governance artifact missing: {core_file}',
            })

    # Fast-path: missing CODEOWNERS → deterministic exit
    codeowners_path = repo_path / '.github' / 'CODEOWNERS'
    if not codeowners_path.is_file():
        drift_items = [
            {
                'severity': 'high',
                'rule': 'CODEOWNERS_presence',
                'message': 'Required CODEOWNERS file is missing.',
            }
        ]
        report = build_report(drift_items)
        write_report(report, json_out, md_out)
        return 2

    # ----------------------------------------------------------------
    # Parse CODEOWNERS rules
    # ----------------------------------------------------------------
    patterns = set()
    for line in codeowners_path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        token = line.split()[0]
        patterns.add(normalize_pattern(token))

    # ----------------------------------------------------------------
    # Validate required rules
    # ----------------------------------------------------------------
    for required in REQUIRED_RULES:
        if normalize_pattern(required) not in patterns:
            drift_items.append({
                'severity': 'high',
                'rule': required,
                'message': f'Required CODEOWNERS rule missing: {required}',
            })

    # ----------------------------------------------------------------
    # Final report
    # ----------------------------------------------------------------
    report = build_report(drift_items)
    write_report(report, json_out, md_out)

    # Exit code: 0 if no drift, 2 if high severity drift
    if any(drift['severity'] == 'high' for drift in drift_items):
        return 2
    return 0


# --------------------------------------------------------------------
# CLI entrypoint
# --------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Detect governance drift and emit JSON/Markdown reports')
    parser.add_argument('--repo', default='.', help='Repository root')
    parser.add_argument('--json-out', default='governance/drift-report.json', help='JSON report path')
    parser.add_argument('--md-out', default='governance/drift-report.md', help='Markdown report path')
    args = parser.parse_args()

    exit_code = check_governance_drift(
        Path(args.repo).resolve(),
        Path(args.json_out),
        Path(args.md_out),
    )
    sys.exit(exit_code)
