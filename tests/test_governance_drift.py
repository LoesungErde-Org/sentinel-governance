import json
from pathlib import Path

from tools.check_governance_drift import check_governance_drift


def _run_checker(repo: Path) -> tuple[int, dict]:
    exit_code = check_governance_drift(
        repo,
        Path("governance/drift-report.json"),
        Path("governance/drift-report.md"),
    )
    report = json.loads(
        (repo / "governance" / "drift-report.json").read_text(encoding="utf-8")
    )
    return exit_code, report


def _write_core_files(repo: Path, codeowners: str) -> None:
    (repo / ".github").mkdir(parents=True)
    (repo / "governance").mkdir(parents=True)
    (repo / ".github" / "CODEOWNERS").write_text(codeowners, encoding="utf-8")
    (repo / "governance" / "repository-governance.md").write_text(
        "# Governance\n", encoding="utf-8"
    )


def test_missing_codeowners_returns_a_single_presence_finding(tmp_path: Path) -> None:
    (tmp_path / "governance").mkdir()
    (tmp_path / "governance" / "repository-governance.md").write_text(
        "# Governance\n", encoding="utf-8"
    )

    exit_code, report = _run_checker(tmp_path)

    assert exit_code == 2
    assert report["drift"] == [
        {
            "severity": "high",
            "rule": "CODEOWNERS_presence",
            "message": "Required CODEOWNERS file is missing.",
        }
    ]


def test_leading_slashes_in_required_rules_are_normalized(tmp_path: Path) -> None:
    _write_core_files(
        tmp_path,
        "\n".join(
            [
                "/.github/workflows/* @owners",
                "/governance/** @owners",
                "/tools/** @owners",
                "/detections/** @owners",
            ]
        ),
    )

    exit_code, report = _run_checker(tmp_path)

    assert exit_code == 0
    assert report["drift"] == []
    assert report["recommendations"] == []


def test_missing_required_rule_is_reported(tmp_path: Path) -> None:
    _write_core_files(
        tmp_path,
        "\n".join(
            [
                ".github/workflows/* @owners",
                "governance/** @owners",
                "tools/** @owners",
            ]
        ),
    )

    exit_code, report = _run_checker(tmp_path)

    assert exit_code == 2
    assert report["drift"] == [
        {
            "severity": "high",
            "rule": "detections/**",
            "message": "Required CODEOWNERS rule missing: detections/**",
        }
    ]
