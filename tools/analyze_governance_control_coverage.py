#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


SENSITIVE_ROOTS = [
    '.github/workflows/',
    'governance/',
    'tools/',
    'detections/',
]

EXPECTED_CONTROLS = [
    {'path': 'governance/repository-governance.md', 'severity': 'high', 'name': 'Repository Governance Policy'},
    {'path': '.github/workflows/detections-ci.yml', 'severity': 'medium', 'name': 'Detection CI Pipeline'},
    {'path': '.github/CODEOWNERS', 'severity': 'medium', 'name': 'Governed Path Ownership'},
    {'path': '.github/workflows/governance-guard.yml', 'severity': 'medium', 'name': 'Governance Guard Workflow'},
]


@dataclass
class Finding:
    severity: str  # low|medium|high
    kind: str
    message: str
    artifact: str


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def codeowners_patterns(path: Path) -> list[str]:
    if not path.is_file():
        return []
    patterns = []
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if parts:
            patterns.append(parts[0])
    return patterns


def workflow_patterns(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = read_text(path)
    patterns = []
    for marker in ["name.startsWith('.github/workflows/')", "name.startsWith('governance/')", "name.startsWith('tools/')", "name.startsWith('detections/')"]:
        if marker in text:
            if "'.github/workflows/'" in marker:
                patterns.append('/.github/workflows/**')
            elif "'governance/'" in marker:
                patterns.append('/governance/**')
            elif "'tools/'" in marker:
                patterns.append('/tools/**')
            elif "'detections/'" in marker:
                patterns.append('/detections/**')
    return patterns


def pattern_to_regex(pattern: str) -> re.Pattern:
    p = pattern.strip()
    if p.startswith('/'):
        p = p[1:]
    p = re.escape(p)
    p = p.replace(r'\*\*', '.*')
    p = p.replace(r'\*', '[^/]*')
    return re.compile(r'^' + p + r'$')


def matches(path: str, patterns: list[str]) -> bool:
    for p in patterns:
        if pattern_to_regex(p).match(path):
            return True
    return False


def classify(findings: list[Finding], coverage_score: float) -> tuple[str, int]:
    if any(f.severity == 'high' for f in findings):
        return 'critical', 2
    if any(f.severity == 'medium' for f in findings) or coverage_score < 85.0:
        return 'warning', 1
    if any(f.severity == 'low' for f in findings):
        return 'warning', 1
    return 'ok', 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Analyze governance control coverage')
    parser.add_argument('--repo', default='.', help='Repository root')
    parser.add_argument('--json-out', default='governance/control-coverage-report.json')
    parser.add_argument('--md-out', default='governance/control-coverage-report.md')
    args = parser.parse_args()

    repo = Path(args.repo).resolve()

    findings: list[Finding] = []
    missing_controls = []
    orphan_controls = []

    for c in EXPECTED_CONTROLS:
        if not (repo / c['path']).is_file():
            missing_controls.append(c['path'])
            findings.append(Finding(c['severity'], 'missing_control', f"Expected control missing: {c['name']}", c['path']))

    patterns = []
    patterns.extend(codeowners_patterns(repo / '.github/CODEOWNERS'))
    patterns.extend(workflow_patterns(repo / '.github/workflows/governance-guard.yml'))
    patterns = sorted(set(patterns))

    for p in patterns:
        test = p[1:] if p.startswith('/') else p
        root = test.split('*')[0].rstrip('/')
        if root and not (repo / root).exists():
            orphan_controls.append(p)
            findings.append(Finding('low', 'orphan_control_pattern', 'Control pattern does not match any existing repository path.', p))

    sensitive_files = []
    for rel in SENSITIVE_ROOTS:
        root = repo / rel.rstrip('/')
        if root.exists():
            sensitive_files.extend([str(p.relative_to(repo)).replace('\\', '/') for p in root.rglob('*') if p.is_file()])

    sensitive_files = sorted(set(sensitive_files))
    ungoverned = []

    if patterns:
        for f in sensitive_files:
            if not matches(f, patterns):
                ungoverned.append(f)
    else:
        ungoverned = sensitive_files.copy()

    if ungoverned:
        sev = 'medium'
        findings.append(Finding(sev, 'ungoverned_paths', f'{len(ungoverned)} sensitive files are not covered by governance control patterns.', 'multiple'))

    covered = max(0, len(sensitive_files) - len(ungoverned))
    coverage_score = 100.0 if not sensitive_files else round((covered / len(sensitive_files)) * 100.0, 2)

    gate_status, exit_code = classify(findings, coverage_score)

    actions = []
    if missing_controls:
        actions.append('Add missing governance controls and rerun coverage analyzer.')
    if ungoverned:
        actions.append('Extend CODEOWNERS or governance guard patterns to cover ungoverned sensitive files.')
    if orphan_controls:
        actions.append('Remove or correct orphan governance control patterns.')
    if not actions:
        actions.append('No action required.')

    report = {
        'coverage_score': coverage_score,
        'gate_status': gate_status,
        'missing_controls': sorted(missing_controls),
        'orphan_controls': sorted(orphan_controls),
        'ungoverned_paths': sorted(ungoverned)[:200],
        'sensitive_file_count': len(sensitive_files),
        'governed_file_count': covered,
        'findings': [asdict(f) for f in findings],
        'recommended_actions': actions,
        'exit_code': exit_code,
    }

    json_out = repo / args.json_out
    md_out = repo / args.md_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)

    json_out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    lines = [
        '# Governance Control Coverage Report',
        '',
        f"- Coverage score: `{coverage_score}%`",
        f"- Gate status: `{gate_status}`",
        f"- Sensitive files: `{len(sensitive_files)}`",
        f"- Governed files: `{covered}`",
        f"- Missing controls: `{len(missing_controls)}`",
        f"- Ungoverned paths: `{len(ungoverned)}`",
        '',
        '| Severity | Type | Artifact | Message |',
        '|---|---|---|---|',
    ]

    if findings:
        for f in findings:
            lines.append(f"| {f.severity} | {f.kind} | `{f.artifact}` | {f.message} |")
    else:
        lines.append('| none | none | `n/a` | No coverage findings. |')

    lines.extend(['', '## Recommended Actions'])
    lines.extend([f'- {a}' for a in actions])

    lines.extend(['', '## References', '- `governance/governance-evidence-matrix.md`', '- `.github/CODEOWNERS`', '- `.github/workflows/governance-guard.yml`'])

    if ungoverned:
        lines.extend(['', '## Ungoverned Paths (sample)'])
        for p in sorted(ungoverned)[:30]:
            lines.append(f'- `{p}`')

    md_out.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print(f'Wrote JSON report: {json_out}')
    print(f'Wrote Markdown report: {md_out}')
    print(f'Coverage score={coverage_score} gate_status={gate_status} exit_code={exit_code}')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

