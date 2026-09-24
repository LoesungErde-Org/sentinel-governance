#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

ISSUER = 'https://token.actions.githubusercontent.com'

DEFAULT_ARTIFACTS = [
    ('governance/forecast.json', 'governance/signatures/forecast.json.sig', 'governance/signatures/forecast.json.pem'),
    ('governance/baselines/detection-snapshot.json', 'governance/signatures/detection-snapshot.json.sig', 'governance/signatures/detection-snapshot.json.pem'),
    ('governance/compiled-rules.json', 'governance/signatures/compiled-rules.json.sig', 'governance/signatures/compiled-rules.json.pem'),
]


def verify_one(workflow_ref: str, file_path: str, sig_path: str, cert_path: str):
    for p in [file_path, sig_path, cert_path]:
        if not Path(p).exists():
            raise FileNotFoundError(f'Missing required signature artifact: {p}')

    if not workflow_ref.startswith('https://github.com/'):
        workflow_ref = f'https://github.com/{workflow_ref}'

    cmd = [
        'cosign',
        'verify-blob',
        '--certificate-identity',
        workflow_ref,
        '--certificate-oidc-issuer',
        ISSUER,
        '--signature',
        sig_path,
        '--certificate',
        cert_path,
        file_path,
    ]
    print(' '.join(cmd))
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description='Verify cosign keyless signatures for governance artifacts')
    parser.add_argument('--workflow-ref', required=True, help='Expected GitHub workflow identity (e.g. github.workflow_ref)')
    parser.add_argument('--include-cab', action='store_true', help='Also verify CAB report signature')

    # Single-artifact mode (used by rollback flow)
    parser.add_argument('--artifact', help='Single artifact to verify')
    parser.add_argument('--signature', help='Signature file for single artifact')
    parser.add_argument('--certificate', help='Certificate file for single artifact')

    args = parser.parse_args()

    if args.artifact or args.signature or args.certificate:
        if not (args.artifact and args.signature and args.certificate):
            raise SystemExit('Single-artifact mode requires --artifact, --signature and --certificate together.')
        verify_one(args.workflow_ref, args.artifact, args.signature, args.certificate)
        print('Single artifact signature verified successfully.')
        return

    artifacts = list(DEFAULT_ARTIFACTS)
    if args.include_cab:
        artifacts.append(('governance/cab-report.md', 'governance/signatures/cab-report.md.sig', 'governance/signatures/cab-report.md.pem'))

    for file_path, sig_path, cert_path in artifacts:
        verify_one(args.workflow_ref, file_path, sig_path, cert_path)

    print('All signatures verified successfully.')


if __name__ == '__main__':
    main()
