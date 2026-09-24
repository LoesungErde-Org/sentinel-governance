from pathlib import Path

from tools import verify_signatures


def test_verify_one_uses_supported_cosign_verify_flags(
    tmp_path: Path, monkeypatch
) -> None:
    artifact = tmp_path / "artifact.json"
    signature = tmp_path / "artifact.sig"
    certificate = tmp_path / "artifact.pem"
    for path in (artifact, signature, certificate):
        path.write_text("fixture", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(command: list[str], check: bool) -> None:
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr(verify_signatures.subprocess, "run", fake_run)

    verify_signatures.verify_one(
        "LoesungErde-Org/sentinel-governance/.github/workflows/detections-ci.yml@refs/heads/main",
        str(artifact),
        str(signature),
        str(certificate),
    )

    command = captured["command"]
    assert command[:2] == ["cosign", "verify-blob"]
    assert "--yes" not in command
    identity_index = command.index("--certificate-identity")
    assert command[identity_index + 1] == (
        "https://github.com/LoesungErde-Org/sentinel-governance/"
        ".github/workflows/detections-ci.yml@refs/heads/main"
    )
    assert "--certificate-oidc-issuer" in command
    assert captured["check"] is True
