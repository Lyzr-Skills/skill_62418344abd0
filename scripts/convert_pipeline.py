#!/usr/bin/env python3
"""
Azure Release Pipeline JSON -> YAML Converter
=============================================
Converts an Azure DevOps Classic Release Pipeline JSON definition
into a modern Azure Pipelines multi-stage YAML file.

Usage:
    python convert_pipeline.py <input.json> [--out <output.yaml>]
"""

import json
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Well-known task GUID -> (name, major_version) lookup
# Sourced from azure-pipelines-tasks repository
# ---------------------------------------------------------------------------
TASK_GUID_MAP = {
    "9c3e8943-130d-4c78-ac63-8af81df62dfb": ("VSBuild", 1),
    "71a9a2d3-a98a-4caa-96ab-affca411ecda": ("PowerShell", 2),
    "e213ff0f-5d5c-4791-802d-52ea3e7be1f1": ("PowerShell", 2),
    "d9bafed4-0b18-4f58-968d-86655b4d2ce9": ("CmdLine", 2),
    "6c731c3c-3c68-459a-a5c9-bde6e6595b5b": ("CopyFiles", 2),
    "2a6f5f40-0d36-4ff7-9edd-6b6d77b4cf23": ("DeleteFiles", 1),
    "7c6a6b71-4355-4e1b-ab14-44b07e4b7a6f": ("PublishBuildArtifacts", 1),
    "a8515ec8-7254-4ffd-912c-86772e2b5962": ("DownloadBuildArtifacts", 0),
    "61f2a582-95ae-4948-b34d-a1b3c4f6a737": ("NuGetToolInstaller", 0),
    "333b11bd-d341-40d9-afcf-b32d5ce6f23b": ("NuGetCommand", 2),
    "ac4ee482-65da-4485-a532-7b085873ddba": ("Maven", 3),
    "0675668a-7bba-4ccb-901d-5ad6554ca653": ("Gradle", 2),
    "7b5a6198-930e-4bc5-80f9-cb60bfea1e1a": ("DotNetCoreCLI", 2),
    "4b8d6346-fd11-4172-b26d-a5c5c1fb55b5": ("NodeTool", 0),
    "npmAuthenticate@0": ("npmAuthenticate", 0),
    "fe47e961-9fa8-4106-8639-368c022d43ad": ("Npm", 1),
    "2ff763a7-ce83-4e1f-bc89-0ae63477cebe": ("UsePythonVersion", 0),
    "1d9b6f5e-2cf1-4e3e-aafc-6a1e2e3e0f8c": ("PythonScript", 0),
    "3b4e0e33-d79f-4e97-b7b5-ef1c19a7d5ad": ("Docker", 2),
    "8d2c8a62-c4d0-49a3-8c3e-0a0b7a3a8b3a": ("KubernetesManifest", 0),
    "2e536346-de1a-469e-aea2-b8d000853a61": ("AzureFunctionApp", 1),
    "497d490f-eea7-4f2b-ab94-48d9c1acdcb1": ("AzureRmWebAppDeployment", 4),
    "4dda660c-b643-4598-a4a2-61080d0002d9": ("AzureAppServiceSettings", 1),
    "2ca8fe15-42ea-4b26-80f1-e0738ec17e89": ("AzureCLI", 2),
    "1e244d32-2dd4-4165-96fb-b7441ca9331e": ("AzurePowerShell", 5),
    "94a74903-f93f-4075-884f-dc11f34058b4": ("AzureKeyVault", 2),
    "b7b1f1c9-ee60-44ea-b7e6-1f77bfc2c6e2": ("SqlAzureDacpacDeployment", 1),
    "3ab11522-a7b4-47bc-8f22-6d2a1e3d9e1f": ("AzureResourceManagerTemplateDeployment", 3),
    "6f8c69a5-b023-428e-a125-fccf4d230905": ("FtpUpload", 2),
    "5bfb729a-a7c8-4a78-a7c3-20002a0a4c3a": ("ExtractFiles", 1),
    "8c3741e7-4fd9-4e26-9a2a-b9e0b2f9c83b": ("ArchiveFiles", 2),
    "c1e1d6ae-5a7d-4f87-ab91-4a7c62c16d3b": ("PublishTestResults", 2),
    "0b0f01ed-7dde-43ff-9cbb-e48954daf9b1": ("VSTest", 2),
    "4eb2ef64-f1c3-4de7-ab35-d2bb0d5e8ad5": ("UseDotNet", 2),
    "e3a1bd71-7a0d-44cf-a8a6-1e3e52b3e5d5": ("JavaToolInstaller", 0),
    "de9ce4e3-d547-43cc-b7df-b8571f54b9fb": ("Bash", 3),
    "f3ab91e7-72b4-4df9-ab5c-0c77b3e0e5a2": ("SSH", 0),
    "1b6c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e": ("WindowsMachineFileCopy", 2),
    "9a4e4fce-c99b-4b5a-9ae2-ea00ce6db2ef": ("ServiceFabricDeploy", 1),
    "df9b5880-9e21-4b72-988e-17c5f6a28768": ("AzureContainerApps", 1),
    "c6f85bf2-0e0d-4073-a84c-1f5b1a0b2e4d": ("TerraformInstaller", 0),
    "5e09a40c-5c18-4e2b-a1d1-7f28e0a5e1b9": ("TerraformTaskV4", 4),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize_identifier(name: str) -> str:
    """Convert a display name to a valid YAML/pipeline identifier."""
    s = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if s and s[0].isdigit():
        s = "Stage_" + s
    return s.strip("_") or "Stage"


def indent(text: str, spaces: int) -> str:
    """Indent every line of text by the given number of spaces."""
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def resolve_task(task_id: str, task_name: str, version: str) -> tuple[str, bool]:
    """
    Return (yaml_task_reference, is_known).
    E.g. ("PowerShell@2", True) or ("9c3e8943-130d...@1  # TODO: verify task name", False)
    """
    guid_clean = task_id.strip("{}").lower() if task_id else ""
    if guid_clean in TASK_GUID_MAP:
        name, major = TASK_GUID_MAP[guid_clean]
        try:
            ver = int(str(version).split(".")[0])
        except (ValueError, TypeError):
            ver = major
        return f"{name}@{ver}", True
    # Fallback: use the name from the JSON if available
    if task_name:
        try:
            ver = int(str(version).split(".")[0])
        except (ValueError, TypeError):
            ver = 1
        return f"{task_name}@{ver}  # TODO: verify task name/version (GUID: {task_id})", False
    return f"UnknownTask@1  # TODO: unknown GUID {task_id}", False


def render_value(v) -> str:
    """Render a Python value as a YAML scalar."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None:
        return "''"
    s = str(v)
    # Quote strings that look like YAML booleans, nulls, or contain special chars
    needs_quote = (
        s.lower() in {"true", "false", "yes", "no", "null", "~", ""}
        or s.startswith(("@", "*", "&", "!", "|", ">", "'", '"', "{", "[", "-"))
        or ":" in s
        or "#" in s
        or "\n" in s
    )
    if needs_quote:
        escaped = s.replace("'", "''")
        return f"'{escaped}'"
    return s


def render_inputs(inputs: dict, base_indent: int = 6) -> str:
    """Render a task inputs dict as indented YAML key-value pairs."""
    if not inputs:
        return ""
    lines = ["inputs:"]
    for k, v in inputs.items():
        if isinstance(v, str) and "\n" in v:
            lines.append(f"  {k}: |")
            for line in v.splitlines():
                lines.append(f"    {line}")
        else:
            lines.append(f"  {k}: {render_value(v)}")
    return indent("\n".join(lines), base_indent)


def render_variables(variables: dict | list, base_indent: int = 2) -> str:
    """Render variables (dict or list of {name,value} objects) as YAML."""
    if not variables:
        return ""
    lines = ["variables:"]
    if isinstance(variables, list):
        for item in variables:
            if "groupId" in item or item.get("isGroup"):
                lines.append(f"  - group: {render_value(item.get('name', item.get('groupName', 'unknown-group')))}")
            else:
                name = item.get("name", "")
                val = item.get("value", "")
                secret = item.get("isSecret", False)
                if secret:
                    lines.append(f"  {name}: ${{{{ variables['{name}'] }}}}  # secret — link via Variable Library")
                else:
                    lines.append(f"  {name}: {render_value(val)}")
    elif isinstance(variables, dict):
        for name, meta in variables.items():
            if isinstance(meta, dict):
                val = meta.get("value", "")
                secret = meta.get("isSecret", False)
                if secret:
                    lines.append(f"  {name}: ${{{{ variables['{name}'] }}}}  # secret — link via Variable Library")
                else:
                    lines.append(f"  {name}: {render_value(val)}")
            else:
                lines.append(f"  {name}: {render_value(meta)}")
    return indent("\n".join(lines), base_indent)


# ---------------------------------------------------------------------------
# Task converter
# ---------------------------------------------------------------------------

def convert_task(task: dict) -> str:
    """Convert a single workflowTask JSON object to YAML step text."""
    lines = []
    enabled = task.get("enabled", True)
    task_id = task.get("taskId", "")
    version = task.get("version", "1.*")
    display_name = task.get("name", "")
    inputs = task.get("inputs", {})
    condition = task.get("condition", "")
    continue_on_error = task.get("continueOnError", False)
    timeout = task.get("timeoutInMinutes", 0)

    if not enabled:
        lines.append(f"# DISABLED: {display_name}")
        return "\n".join(lines)

    task_ref, _known = resolve_task(task_id, display_name, version)

    # Special handling: inline script tasks
    if task_id.strip("{}").lower() in {
        "e213ff0f-5d5c-4791-802d-52ea3e7be1f1",  # PowerShell
        "71a9a2d3-a98a-4caa-96ab-affca411ecda",  # PowerShell inline
    }:
        script_body = inputs.get("script", inputs.get("ScriptBody", ""))
        if script_body:
            lines.append(f"- task: {task_ref}")
            if display_name:
                lines.append(f"  displayName: '{display_name}'")
            lines.append("  inputs:")
            lines.append("    targetType: inline")
            lines.append("    script: |")
            for sline in script_body.splitlines():
                lines.append(f"      {sline}")
            remaining = {k: v for k, v in inputs.items() if k not in ("script", "ScriptBody", "targetType")}
            for k, v in remaining.items():
                lines.append(f"    {k}: {render_value(v)}")
            if condition:
                lines.append(f"  condition: {condition}")
            if continue_on_error:
                lines.append("  continueOnError: true")
            if timeout:
                lines.append(f"  timeoutInMinutes: {timeout}")
            return "\n".join(lines)

    lines.append(f"- task: {task_ref}")
    if display_name:
        lines.append(f"  displayName: '{display_name}'")
    if inputs:
        lines.append("  inputs:")
        for k, v in inputs.items():
            if isinstance(v, str) and "\n" in v:
                lines.append(f"    {k}: |")
                for sline in v.splitlines():
                    lines.append(f"      {sline}")
            else:
                lines.append(f"    {k}: {render_value(v)}")
    if condition:
        lines.append(f"  condition: {condition}")
    if continue_on_error:
        lines.append("  continueOnError: true")
    if timeout:
        lines.append(f"  timeoutInMinutes: {timeout}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deploy phase converter
# ---------------------------------------------------------------------------

def convert_deploy_phase(phase: dict, env_name: str) -> str:
    """Convert a deployPhase JSON object to a YAML job block."""
    phase_type = phase.get("phaseType", 1)  # 1=agent, 2=agentless/server, 3=machineGroup
    phase_name = sanitize_identifier(phase.get("name", "Deploy"))
    display_name = phase.get("name", "Deploy")
    deployment_input = phase.get("deploymentInput", {})
    tasks = phase.get("workflowTasks", [])
    timeout = deployment_input.get("timeoutInMinutes", 0)

    # Resolve agent pool
    queue_id = deployment_input.get("queueId")
    queue_name = deployment_input.get("queueName") or deployment_input.get("demands", [{}])
    if isinstance(deployment_input.get("agentPool"), dict):
        pool_name = deployment_input["agentPool"].get("name", "Default")
    elif queue_name and isinstance(queue_name, str):
        pool_name = queue_name
    else:
        pool_name = "Default  # TODO: verify agent pool name"

    lines = []

    if phase_type == 2:
        # Agentless / server job
        lines.append(f"- job: {phase_name}")
        lines.append(f"  displayName: '{display_name}'")
        lines.append("  pool: server")
        if timeout:
            lines.append(f"  timeoutInMinutes: {timeout}")
        if tasks:
            lines.append("  steps:")
            for task in tasks:
                step_yaml = convert_task(task)
                lines.append(indent(step_yaml, 4))
        return "\n".join(lines)

    if phase_type == 3:
        # Deployment group
        dg_name = deployment_input.get("deploymentGroupName", "YourDeploymentGroup")
        lines.append(f"- deployment: {phase_name}")
        lines.append(f"  displayName: '{display_name}'")
        lines.append(f"  environment:")
        lines.append(f"    name: {sanitize_identifier(env_name)}")
        lines.append(f"    resourceType: VirtualMachine")
        lines.append(f"    tags: '{dg_name}'  # TODO: map to deployment group tags")
        if timeout:
            lines.append(f"  timeoutInMinutes: {timeout}")
        lines.append("  strategy:")
        lines.append("    runOnce:")
        lines.append("      deploy:")
        lines.append("        steps:")
        for task in tasks:
            step_yaml = convert_task(task)
            lines.append(indent(step_yaml, 10))
        return "\n".join(lines)

    # Default: agent-based deployment job
    parallel = phase.get("parallelExecution", {})
    parallel_type = parallel.get("parallelExecutionType", 0)  # 0=none,1=multiMachine,2=multiConfig

    lines.append(f"- deployment: {phase_name}")
    lines.append(f"  displayName: '{display_name}'")
    lines.append(f"  pool:")
    lines.append(f"    name: {pool_name}")
    lines.append(f"  environment: {sanitize_identifier(env_name)}")
    if timeout:
        lines.append(f"  timeoutInMinutes: {timeout}")

    if parallel_type == 2:
        # Multi-configuration
        multiplier = parallel.get("multiplier", "")
        lines.append("  strategy:")
        lines.append("    matrix:")
        lines.append(f"      # TODO: define matrix from multiplier variable '{multiplier}'")
        lines.append("      config1:")
        lines.append(f"        {multiplier}: value1")
        lines.append("      deploy:")
        lines.append("        steps:")
        for task in tasks:
            step_yaml = convert_task(task)
            lines.append(indent(step_yaml, 10))
    else:
        lines.append("  strategy:")
        lines.append("    runOnce:")
        lines.append("      deploy:")
        lines.append("        steps:")
        for task in tasks:
            step_yaml = convert_task(task)
            lines.append(indent(step_yaml, 10))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Environment/Stage converter
# ---------------------------------------------------------------------------

def convert_environment(env: dict, prev_env_name: str | None = None, rank: int = 0) -> str:
    """Convert an environment JSON object to a YAML stage block."""
    env_name = env.get("name", f"Stage_{rank}")
    stage_id = sanitize_identifier(env_name)
    conditions = env.get("conditions", [])
    variables = env.get("variables", {})
    phases = env.get("deployPhases", [])
    pre_approvals = env.get("preDeployApprovals", {})
    post_approvals = env.get("postDeployApprovals", {})
    env_options = env.get("environmentOptions", {})
    timeout = env_options.get("timeoutInMinutes", 0)

    lines = []
    lines.append(f"- stage: {stage_id}")
    lines.append(f"  displayName: '{env_name}'")

    # Determine dependsOn
    if rank == 0:
        lines.append("  dependsOn: []")
    elif prev_env_name:
        lines.append(f"  dependsOn: {sanitize_identifier(prev_env_name)}")

    # Condition logic
    cond_str = "succeeded()"
    for cond in conditions:
        cond_type = cond.get("conditionType", 1)
        if cond_type == 4:  # environmentState
            cond_str = "succeeded()"
        elif cond_type == 1:  # artifact
            cond_str = "succeeded()"
        elif cond_type == 6:
            cond_str = "always()"
    lines.append(f"  condition: {cond_str}")

    # Approvals
    pre_gates = pre_approvals.get("approvals", [])
    pre_manual = [a for a in pre_gates if not a.get("isAutomated", True)]
    if pre_manual:
        lines.append(f"  # APPROVAL REQUIRED: {len(pre_manual)} pre-deployment approval(s).")
        lines.append(f"  # Configure as Environment Checks in the Azure DevOps Environments UI.")

    post_gates = post_approvals.get("approvals", [])
    post_manual = [a for a in post_gates if not a.get("isAutomated", True)]
    if post_manual:
        lines.append(f"  # APPROVAL REQUIRED: {len(post_manual)} post-deployment approval(s).")
        lines.append(f"  # Configure as Environment Checks in the Azure DevOps Environments UI.")

    if timeout:
        lines.append(f"  timeoutInMinutes: {timeout}")

    # Stage-level variables
    if variables:
        var_block = render_variables(variables, base_indent=0)
        if var_block:
            for vline in var_block.splitlines():
                lines.append(f"  {vline}")

    # Jobs
    if phases:
        lines.append("  jobs:")
        for phase in phases:
            job_yaml = convert_deploy_phase(phase, env_name)
            lines.append(indent(job_yaml, 4))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Artifacts / Resources
# ---------------------------------------------------------------------------

def convert_artifacts(artifacts: list) -> str:
    """Convert artifact definitions to a resources block."""
    if not artifacts:
        return ""
    lines = ["resources:"]
    pipelines = [a for a in artifacts if a.get("type", "").lower() in ("build", "")]
    repos = [a for a in artifacts if a.get("type", "").lower() == "git"]

    if pipelines:
        lines.append("  pipelines:")
        for art in pipelines:
            alias = sanitize_identifier(art.get("alias", "build"))
            definition_ref = art.get("definitionReference", {})
            source = definition_ref.get("definition", {}).get("name", "YourBuildPipeline")
            project_val = definition_ref.get("project", {}).get("name", "")
            branch = definition_ref.get("defaultVersionBranch", {}).get("id", "main")
            lines.append(f"  - pipeline: {alias}")
            lines.append(f"    source: '{source}'")
            if project_val:
                lines.append(f"    project: '{project_val}'")
            lines.append("    trigger:")
            lines.append(f"      branches:")
            lines.append(f"        include:")
            lines.append(f"          - {branch}")

    if repos:
        lines.append("  repositories:")
        for art in repos:
            alias = sanitize_identifier(art.get("alias", "repo"))
            definition_ref = art.get("definitionReference", {})
            repo_url = definition_ref.get("definition", {}).get("name", "YourRepo")
            branch = definition_ref.get("defaultVersionBranch", {}).get("id", "main")
            lines.append(f"  - repository: {alias}")
            lines.append(f"    type: git")
            lines.append(f"    name: '{repo_url}'")
            lines.append(f"    ref: refs/heads/{branch}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduled triggers
# ---------------------------------------------------------------------------

def convert_schedules(triggers: list) -> str:
    """Convert release schedule triggers to YAML schedules block."""
    schedules = [t for t in triggers if t.get("triggerType", 0) == 2]
    if not schedules:
        return ""
    lines = ["schedules:"]
    for sched in schedules:
        schedule = sched.get("schedule", {})
        cron = schedule.get("cronExpression", "0 2 * * *")
        branch = schedule.get("branchFilter", {}).get("include", ["main"])
        if isinstance(branch, list) and branch:
            branch_val = branch[0]
        else:
            branch_val = "main"
        lines.append(f"- cron: '{cron}'")
        lines.append(f"  displayName: Scheduled Release")
        lines.append(f"  branches:")
        lines.append(f"    include:")
        lines.append(f"      - {branch_val}")
        lines.append(f"  always: false")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def convert(data: dict) -> str:
    """Convert a parsed release pipeline dict to a YAML string."""
    name = data.get("name", "release-pipeline")
    artifacts = data.get("artifacts", [])
    environments = data.get("environments", [])
    variables = data.get("variables", {})
    triggers = data.get("triggers", [])

    sections = []

    # Header comment
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    sections.append(
        f"# Generated by azure-pipeline-converter skill\n"
        f"# Source: {name}\n"
        f"# Converted: {now}\n"
        f"# Review all '# TODO' and '# APPROVAL REQUIRED' comments before committing.\n"
    )

    # Trigger - classic release pipelines are triggered by artifacts
    sections.append("trigger: none\n")

    # Resources (artifact sources)
    resource_block = convert_artifacts(artifacts)
    if resource_block:
        sections.append(resource_block + "\n")
    else:
        sections.append(
            "resources:\n"
            "  pipelines:\n"
            "    - pipeline: build  # TODO: link to your build pipeline\n"
            "      source: 'YourBuildPipeline'\n"
            "      trigger: true\n"
        )

    # Schedules
    schedule_block = convert_schedules(triggers)
    if schedule_block:
        sections.append(schedule_block + "\n")

    # Pipeline-level variables
    if variables:
        var_block = render_variables(variables, base_indent=0)
        if var_block:
            sections.append(var_block + "\n")

    # Stages
    if environments:
        sections.append("stages:")
        prev_name = None
        for i, env in enumerate(environments):
            stage_yaml = convert_environment(env, prev_env_name=prev_name, rank=i)
            sections.append(stage_yaml)
            prev_name = env.get("name")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert Azure DevOps Classic Release Pipeline JSON to YAML"
    )
    parser.add_argument("input", help="Path to input JSON file")
    parser.add_argument("--out", help="Output YAML file path (default: stdout)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON — {e}", file=sys.stderr)
        sys.exit(1)

    yaml_output = convert(data)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(yaml_output)
        print(f"✅  Written to {out_path}")
    else:
        print(yaml_output)

    # Report TODOs
    todos = [line.strip() for line in yaml_output.splitlines() if "# TODO" in line or "# APPROVAL" in line]
    if todos:
        print(f"\n⚠️  {len(todos)} item(s) require manual review:", file=sys.stderr)
        for t in todos:
            print(f"   • {t}", file=sys.stderr)


if __name__ == "__main__":
    main()
