#!/usr/bin/env python3
"""Validate source controls; this does not assert remote ruleset activation."""
import argparse
import json
import re
from pathlib import Path

import yaml


def validate(repo, policy):
    if policy["bypass_actors"] or policy["enforcement"] != "active":
        raise ValueError("Branch quality policy permits bypass or is inactive")
    if policy["conditions"]["ref_name"] != {"include": ["~DEFAULT_BRANCH"], "exclude": []}:
        raise ValueError("Quality ruleset must protect the default branch")
    rules = {r["type"]: r.get("parameters", {}) for r in policy["rules"]}
    for required in ["deletion", "non_fast_forward", "required_signatures", "required_linear_history"]:
        if required not in rules:
            raise ValueError(f"Missing integrity rule: {required}")
    pr = rules["pull_request"]
    if pr["required_approving_review_count"] < 1 or not all(pr[key] for key in [
        "require_code_owner_review", "dismiss_stale_reviews_on_push", "require_last_push_approval", "required_review_thread_resolution"
    ]):
        raise ValueError("Missing independent review control")
    checks = rules["required_status_checks"]
    if not checks["strict_required_status_checks_policy"]:
        raise ValueError("Checks must test the latest base branch")
    available = set()
    for path in (repo / ".github/workflows").glob("*.yml"):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        triggers = workflow.get("on", workflow.get(True, {}))
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if "uses" in step and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"]):
                    raise ValueError(f"Mutable action reference: {path.name}")
                if step.get("uses", "").startswith("actions/checkout@") and step.get("with", {}).get("persist-credentials") is not False:
                    raise ValueError(f"Checkout retains credentials: {path.name}")
        if not isinstance(triggers, dict) or "pull_request" not in triggers or "push" not in triggers:
            continue
        if any((triggers[event] or {}).get(key) for event in ["pull_request", "push"] for key in ["paths", "paths-ignore"]):
            continue
        for job_id, job in workflow["jobs"].items():
            if job.get("if", "always()") == "always()" and "matrix" not in job.get("strategy", {}):
                if job.get("needs") and job.get("if") != "always()":
                    continue
                if job.get("needs") and not any(
                    s.get("run") == 'test "$PRODUCER_RESULT" = success'
                    for s in job.get("steps", [])
                ):
                    continue
                available.add(job.get("name", job_id))
    for check in checks["required_status_checks"]:
        if check["context"] not in available or check.get("integration_id") != 15368:
            raise ValueError(f"Missing unconditional Actions check: {check['context']}")
    return sorted(available)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    policy = json.loads((args.repo / "governance/branch-quality-policy.json").read_text())
    print("Verified source controls; remote activation requires administrator access.")
    print(json.dumps(validate(args.repo, policy)))


if __name__ == "__main__":
    main()
