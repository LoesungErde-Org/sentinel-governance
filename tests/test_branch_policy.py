import copy
import json
import shutil
from pathlib import Path

import pytest

from tools.validate_branch_policy import validate

ROOT = Path(__file__).resolve().parents[1]


def test_reviewed_policy_matches_real_unconditional_jobs():
    policy = json.loads((ROOT / "governance/branch-quality-policy.json").read_text())
    assert "risk-gate" in validate(ROOT, policy)


@pytest.mark.parametrize("mutation", ["bypass", "missing-check", "no-review", "no-signatures"])
def test_weakened_policy_is_rejected(mutation):
    policy = copy.deepcopy(json.loads((ROOT / "governance/branch-quality-policy.json").read_text()))
    if mutation == "bypass":
        policy["bypass_actors"] = [{"actor_id": 1}]
    elif mutation == "missing-check":
        policy["rules"][-1]["parameters"]["required_status_checks"].append({"context": "fictional-pass", "integration_id": 15368})
    elif mutation == "no-review":
        policy["rules"][-2]["parameters"]["required_approving_review_count"] = 0
    else:
        policy["rules"] = [r for r in policy["rules"] if r["type"] != "required_signatures"]
    with pytest.raises(ValueError):
        validate(ROOT, policy)


def test_mutable_action_is_rejected(tmp_path):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    workflow = tmp_path / ".github/workflows/rollback-smoke.yml"
    workflow.write_text(workflow.read_text().replace("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "actions/checkout@v4"))
    policy = json.loads((ROOT / "governance/branch-quality-policy.json").read_text())
    with pytest.raises(ValueError, match="Mutable"):
        validate(tmp_path, policy)


def test_skipped_dependency_cannot_satisfy_required_gate(tmp_path):
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    workflow = tmp_path / ".github/workflows/detections-ci.yml"
    workflow.write_text(workflow.read_text().replace("if: always()", "if: success()"))
    policy = json.loads((ROOT / "governance/branch-quality-policy.json").read_text())
    with pytest.raises(ValueError, match="Missing unconditional"):
        validate(tmp_path, policy)
