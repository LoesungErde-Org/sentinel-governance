#!/usr/bin/env python3
"""Default: print the reviewed payload. --apply requires an administrator gh session."""
import argparse
import json
import subprocess

from validate_branch_policy import validate
from pathlib import Path


def api(endpoint, method="GET", payload=None):
    command = ["gh", "api", "--method", method, endpoint]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="LoesungErde-Org/sentinel-governance")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.repo != "LoesungErde-Org/sentinel-governance":
        raise SystemExit("This payload is bound to sentinel-governance's verified CI check names.")
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / "governance/branch-quality-policy.json").read_text())
    validate(root, policy)
    if not args.apply:
        print(json.dumps(policy, indent=2))
        return
    # Prevent activating checks before this PR's workflow definitions are merged.
    remote = api(f"repos/{args.repo}/contents/governance/branch-quality-policy.json?ref=main")
    import base64
    if json.loads(base64.b64decode(remote["content"])) != policy:
        raise SystemExit("Merge and verify this exact policy on main before activation.")
    existing = api(f"repos/{args.repo}/rulesets")
    matches = [r for r in existing if r["name"] == policy["name"]]
    if matches:
        raise SystemExit("Named ruleset already exists; review its drift manually. Other rulesets were left intact.")
    created = api(f"repos/{args.repo}/rulesets", "POST", policy)
    verified = api(f"repos/{args.repo}/rulesets/{created['id']}")
    if any(verified[key] != policy[key] for key in ["enforcement", "conditions", "rules", "bypass_actors"]):
        raise SystemExit("Created ruleset differs from policy; administrator review required.")
    print(json.dumps({"ruleset_id": created["id"], "enforcement": verified["enforcement"]}))


if __name__ == "__main__":
    main()
