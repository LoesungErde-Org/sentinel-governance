#!/usr/bin/env python3
"""Build production Sentinel ARM resources from the actual compiled rules."""
import argparse
import hashlib
import json
import re
import tarfile
import uuid
from pathlib import Path

import yaml


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confined(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f"Path outside deployment source: {name}")
    return path


def build(repo, compiled_path, output):
    repo = repo.resolve()
    document = json.loads(compiled_path.read_text(encoding="utf-8-sig"))
    items = document["compiled"]
    if not items or document["count"] != len(items):
        raise ValueError("Empty or inconsistent compiled rule inventory")
    packs = {}
    for item in items:
        if item["env"] != "prod":
            continue
        pack = item["pack"]
        if not re.fullmatch(r"[a-z][a-z0-9-]*", pack):
            raise ValueError("Invalid pack name")
        path = confined(repo, item["file"])
        expected_dir = repo / "detections" / pack / "rules" / "generated"
        if path.parent != expected_dir or path.suffix != ".yaml":
            raise ValueError("Compiled file is not in its generated pack")
        rule = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        metadata, spec = rule["metadata"], rule["spec"]
        if metadata["pack"] != pack or metadata["stable_id"] != item["stable_id"]:
            raise ValueError("Compiled inventory does not match rule identity")
        uuid.UUID(metadata["stable_id"])
        if not any(e["name"] == "prod" for e in spec["environments"]):
            raise ValueError("Rule does not target production")
        function = spec["query"]["sourceFunction"]
        if not re.fullmatch(r"fn_[a-z0-9_]+_v\d+", function):
            raise ValueError("Invalid source function")
        function_path = repo / "detections" / pack / "functions" / f"{function}.kql"
        if not function_path.is_file():
            raise ValueError(f"Missing source function: {function}")
        incident = spec["incident"]
        if metadata["lifecycle"] == "experimental" and incident["createIncident"]:
            raise ValueError("Experimental rule cannot create incidents")
        grouping = incident.get("grouping", {})
        entity_types = {m["entityType"] for m in rule["metadata_ext"]["entityMappings"]}
        group_by = ["Account" if e == "User" else e for e in grouping.get("byEntities", [])]
        group_by = [e for e in group_by if e in entity_types]
        suppress = spec["suppression"]
        props = {
            "displayName": rule["name"], "description": f"Compiled {rule['id']} ({metadata['lifecycle']})",
            "enabled": spec["enabled"], "query": rule["query"],
            "queryFrequency": spec["schedule"]["frequency"], "queryPeriod": spec["schedule"]["lookback"],
            "severity": incident["severity"],
            "suppressionEnabled": suppress.get("enabled", False),
            "suppressionDuration": suppress.get("duration", "PT1H"),
            # The compiled query already filters each entity by its detection threshold.
            "triggerOperator": "GreaterThan", "triggerThreshold": 0,
            "entityMappings": rule["metadata_ext"]["entityMappings"],
            "techniques": metadata["mitre_techniques"],
            "incidentConfiguration": {
                "createIncident": incident["createIncident"],
                "groupingConfiguration": {
                    "enabled": bool(grouping.get("enabled", False) and group_by),
                    "groupByEntities": group_by, "lookbackDuration": grouping.get("lookback", "PT1H"),
                    "matchingMethod": "Selected" if group_by else "AllEntities", "reopenClosedIncident": False,
                },
            },
        }
        entries = packs.setdefault(pack, {"functions": {}, "rules": []})
        entries["functions"][function] = {
            "type": "Microsoft.OperationalInsights/workspaces/savedSearches", "apiVersion": "2020-08-01",
            "name": f"[concat(parameters('workspaceName'), '/{function}')]",
            "properties": {"category": "Sentinel Functions", "displayName": function, "functionAlias": function,
                           "query": function_path.read_text(encoding="utf-8-sig"), "version": 2},
        }
        entries["rules"].append({
            "type": "Microsoft.OperationalInsights/workspaces/providers/alertRules", "apiVersion": "2024-03-01",
            "name": f"[concat(parameters('workspaceName'), '/Microsoft.SecurityInsights/{metadata['stable_id']}')]",
            "kind": "Scheduled", "properties": props,
            "dependsOn": [f"[resourceId('Microsoft.OperationalInsights/workspaces/savedSearches', parameters('workspaceName'), '{function}')]"],
        })
    if not packs:
        raise ValueError("No production rules available for deployment")
    checksums = {}
    for pack, entries in sorted(packs.items()):
        template = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0", "parameters": {"workspaceName": {"type": "string", "minLength": 1}},
            "resources": list(entries["functions"].values()) + entries["rules"],
        }
        target = output / pack / "analyticRules.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
        checksums[str(target.relative_to(output))] = digest(target)
    manifest = {"environment": "prod", "packs": sorted(packs), "checksums": checksums}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(output):
    manifest = json.loads((output / "manifest.json").read_text())
    if manifest["environment"] != "prod" or not manifest["packs"] or not manifest["checksums"]:
        raise ValueError("Empty or non-production deployment")
    expected = {f"{p}/analyticRules.json" for p in manifest["packs"]}
    if set(manifest["checksums"]) != expected:
        raise ValueError("Deployment manifest does not cover every pack")
    for name, checksum in manifest["checksums"].items():
        path = confined(output, name)
        if digest(path) != checksum:
            raise ValueError(f"Deployment checksum mismatch: {name}")
        template = json.loads(path.read_text())
        rules = [r for r in template["resources"] if r.get("kind") == "Scheduled"]
        if not rules or any(r["properties"]["triggerThreshold"] != 0 for r in rules):
            raise ValueError("Missing rules or duplicate query threshold")
    return manifest


def extract(snapshot, destination):
    # Called only AFTER the workflow verifies this snapshot's keyless signature.
    with tarfile.open(snapshot) as archive:
        members = [m for m in archive.getmembers() if m.name == "deploy" or m.name.startswith("deploy/")]
        if not members or any(not (m.isdir() or m.isfile()) for m in members):
            raise ValueError("Missing deployment or unsafe snapshot member")
        archive.extractall(destination, members=members, filter="data")
    return verify(destination / "deploy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify", "extract"])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--compiled", type=Path, default=Path("governance/compiled-rules.json"))
    parser.add_argument("--output", type=Path, default=Path("deploy"))
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.repo, args.compiled, args.output)
    elif args.command == "verify":
        result = verify(args.output)
    else:
        result = extract(args.snapshot, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
