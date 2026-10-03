import importlib.util
import json
import shutil
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


@pytest.fixture
def compiled(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "detections", repo / "detections")
    compiler = module("rule_compiler")
    template = json.loads((ROOT / "templates/mitre-techniques/T1110-password-spray.compiler.json").read_text(encoding="utf-8-sig"))
    params = yaml.safe_load((ROOT / "tools/rule_params.example.yaml").read_text(encoding="utf-8-sig"))
    items = compiler.compile_from_config(repo, template, params, compiler.list_functions(repo))
    inventory = repo / "compiled.json"
    inventory.write_text(json.dumps({"compiled": items, "count": len(items)}))
    return repo, inventory, module("build_deployment")


def test_real_production_resources_and_experimental_control(compiled):
    repo, inventory, builder = compiled
    manifest = builder.build(repo, inventory, repo / "deploy")
    assert manifest["packs"] == ["identity", "network"]
    assert builder.verify(repo / "deploy") == manifest
    for pack in manifest["packs"]:
        resources = json.loads((repo / "deploy" / pack / "analyticRules.json").read_text())["resources"]
        assert len(resources) == 2  # One actual function and one prod rule; no dev duplicates.
        function, rule = resources
        assert function["properties"]["functionAlias"] in rule["properties"]["query"]
        assert rule["properties"]["queryFrequency"] == "PT5M"
        assert rule["properties"]["triggerThreshold"] == 0
        assert rule["properties"]["incidentConfiguration"]["createIncident"] == (pack == "identity")


def test_tampered_template_is_rejected(compiled):
    repo, inventory, builder = compiled
    builder.build(repo, inventory, repo / "deploy")
    (repo / "deploy/identity/analyticRules.json").write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        builder.verify(repo / "deploy")


@pytest.mark.parametrize("mode", ["empty", "outside", "experimental", "missing-function"])
def test_invalid_inventory_is_rejected(compiled, mode):
    repo, inventory, builder = compiled
    doc = json.loads(inventory.read_text())
    prod = next(item for item in doc["compiled"] if item["env"] == "prod")
    if mode == "empty":
        doc = {"compiled": [], "count": 0}
    elif mode == "outside":
        prod["file"] = "/etc/passwd"
    elif mode == "experimental":
        rule_path = Path(prod["file"])
        rule = yaml.safe_load(rule_path.read_text())
        rule["metadata"]["lifecycle"] = "experimental"
        rule["spec"]["incident"]["createIncident"] = True
        rule_path.write_text(yaml.safe_dump(rule))
    else:
        for path in (repo / "detections").glob("*/functions/*.kql"):
            path.unlink()
    inventory.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        builder.build(repo, inventory, repo / "deploy")


def test_signed_snapshot_payload_can_be_restored(compiled):
    repo, inventory, builder = compiled
    builder.build(repo, inventory, repo / "deploy")
    snapshot = repo / "snapshot.tar.gz"
    with tarfile.open(snapshot, "w:gz") as archive:
        archive.add(repo / "deploy", arcname="deploy")
    restored = repo / "restored"
    assert builder.extract(snapshot, restored)["packs"] == ["identity", "network"]
