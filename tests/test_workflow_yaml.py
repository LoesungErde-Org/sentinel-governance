from pathlib import Path

import pytest
import yaml


WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS.glob("*.yml")))
def test_github_workflow_has_valid_yaml(workflow: Path) -> None:
    """A malformed workflow must fail locally instead of disappearing from Actions."""
    try:
        parsed = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        pytest.fail(f"{workflow.name} is not valid YAML: {exc}")

    assert isinstance(parsed, dict), f"{workflow.name} must define a YAML mapping"
