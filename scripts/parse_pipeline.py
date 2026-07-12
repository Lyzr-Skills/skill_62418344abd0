#!/usr/bin/env python3
"""
Azure Release Pipeline JSON Parser
====================================
Extracts and summarises the structure of a Classic Release Pipeline JSON.
Useful for understanding the pipeline before conversion.

Usage:
    python parse_pipeline.py <input.json> [--out parsed.json]
"""

import json
import sys
import argparse
from pathlib import Path


def parse_pipeline(data: dict) -> dict:
    """Extract a structured summary from the raw pipeline JSON."""
    name = data.get("name", "unknown")
    environments = data.get("environments", [])
    artifacts = data.get("artifacts", [])
    variables = data.get("variables", {})
    triggers = data.get("triggers", [])

    summary = {
        "pipeline_name": name,
        "stages_count": len(environments),
        "artifacts_count": len(artifacts),
        "pipeline_variables": list(variables.keys()) if isinstance(variables, dict) else [],
        "has_schedules": any(t.get("triggerType") == 2 for t in triggers),
        "stages": [],
        "artifacts": [],
    }

    for env in environments:
        env_name = env.get("name", "unknown")
        phases = env.get("deployPhases", [])
        env_vars = env.get("variables", {})
        pre_approvals = env.get("preDeployApprovals", {}).get("approvals", [])
        post_approvals = env.get("postDeployApprovals", {}).get("approvals", [])
        pre_manual = [a for a in pre_approvals if not a.get("isAutomated", True)]
        post_manual = [a for a in post_approvals if not a.get("isAutomated", True)]

        tasks_total = sum(len(p.get("workflowTasks", [])) for p in phases)
        phase_types = []
        for p in phases:
            pt = p.get("phaseType", 1)
            phase_types.append({1: "agentBased", 2: "agentless", 3: "machineGroup"}.get(pt, "unknown"))

        stage_info = {
            "name": env_name,
            "rank": env.get("rank", 0),
            "phases": len(phases),
            "phase_types": phase_types,
            "total_tasks": tasks_total,
            "stage_variables": list(env_vars.keys()) if isinstance(env_vars, dict) else [],
            "pre_approvals": len(pre_manual),
            "post_approvals": len(post_manual),
        }
        summary["stages"].append(stage_info)

    for art in artifacts:
        definition_ref = art.get("definitionReference", {})
        art_info = {
            "alias": art.get("alias", ""),
            "type": art.get("type", "Build"),
            "source": definition_ref.get("definition", {}).get("name", ""),
            "project": definition_ref.get("project", {}).get("name", ""),
            "default_branch": definition_ref.get("defaultVersionBranch", {}).get("id", ""),
        }
        summary["artifacts"].append(art_info)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Parse Azure Release Pipeline JSON structure")
    parser.add_argument("input", help="Path to input JSON file")
    parser.add_argument("--out", help="Output JSON file path (default: stdout)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = parse_pipeline(data)
    output = json.dumps(summary, indent=2)

    if args.out:
        out_path = Path(args.out)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅  Parsed summary written to {out_path}")
    else:
        print(output)

    # Print human-readable summary to stderr
    print(f"\n📋  Pipeline: {summary['pipeline_name']}", file=sys.stderr)
    print(f"   Stages:    {summary['stages_count']}", file=sys.stderr)
    print(f"   Artifacts: {summary['artifacts_count']}", file=sys.stderr)
    for s in summary["stages"]:
        approvals = ""
        if s["pre_approvals"]:
            approvals += f"  ⚠️  {s['pre_approvals']} pre-approval(s)"
        if s["post_approvals"]:
            approvals += f"  ⚠️  {s['post_approvals']} post-approval(s)"
        print(f"   • {s['name']} — {s['total_tasks']} task(s){approvals}", file=sys.stderr)


if __name__ == "__main__":
    main()
