---
name: azure-pipeline-converter
description: >
  Converts an Azure DevOps Classic Release Pipeline exported as JSON (via the Azure DevOps REST API
  or UI export) into a modern Azure Pipelines YAML file. Use this skill whenever a user uploads or
  pastes a JSON file describing an Azure Release pipeline, asks to migrate from Classic Release
  pipelines to YAML-based pipelines, wants to modernize their Azure DevOps CI/CD setup, mentions
  terms like "release definition", "classic pipeline", "pipeline as code", or shares a JSON blob
  that looks like an Azure DevOps pipeline export. Even if the user just says "convert my pipeline"
  or "turn this JSON into a pipeline file", trigger this skill if there is any Azure DevOps context.
---

# Azure Release Pipeline JSON → YAML Converter

This skill converts an Azure DevOps **Classic Release Pipeline** definition (exported as JSON) into
a clean, modern **Azure Pipelines YAML** file that can be committed directly to source control and
used with Azure Pipelines multi-stage YAML pipelines.

## Why this matters

Azure DevOps Classic Release Pipelines are configured through the UI and stored server-side as
JSON definitions. Microsoft is progressively encouraging teams to migrate to YAML pipelines because
YAML pipelines live in source control, support PR reviews, enable branching strategies, and provide
full auditability. The JSON export format is rich but complex — this skill knows exactly how to map
every significant field to its YAML equivalent.

---

## Workflow

### Step 1 — Obtain the JSON input

The user will provide the pipeline JSON in one of these ways:
- **File upload**: a `.json` file exported from Azure DevOps
- **Pasted JSON**: raw JSON pasted directly into the chat
- **REST API output**: JSON from `GET https://dev.azure.com/{org}/{project}/_apis/release/definitions/{id}`

If the JSON is not yet available, tell the user:
> "Please export your Classic Release Pipeline from Azure DevOps (Releases → ⋮ → Export) and share
> the `.json` file, or paste the JSON directly here."

---

### Step 2 — Parse and understand the JSON structure

Run the bundled parser script to extract structured data from the JSON:

```bash
python scripts/parse_pipeline.py <input.json> --out parsed.json
```

The key sections to extract are:

| JSON Field | Meaning |
|---|---|
| `name` | Pipeline name |
| `environments[]` | Stages (each environment = one YAML stage) |
| `environments[].deployPhases[]` | Jobs within a stage |
| `environments[].deployPhases[].workflowTasks[]` | Steps/tasks within a job |
| `environments[].conditions[]` | Stage trigger conditions |
| `environments[].preDeployApprovals` / `postDeployApprovals` | Manual approval gates |
| `environments[].variables` | Stage-scoped variables |
| `variables` | Pipeline-level variables |
| `artifacts[]` | Pipeline trigger artifacts (build / repo sources) |
| `triggers[]` | CD trigger configuration |
| `environments[].deployPhases[].deploymentInput.queueId` | Agent pool reference |
| `environments[].environmentOptions` | Environment-level options (timeout, badges) |

---

### Step 3 — Map JSON concepts to YAML concepts

Use this mapping table to produce the YAML. Understanding *why* each mapping exists helps produce
idiomatic output rather than a mechanical transliteration.

#### Top-level structure

```yaml
trigger: none          # Classic Release pipelines are triggered externally;
                       # set to 'none' and add a resources: block for artifact triggers.

resources:
  pipelines:
    - pipeline: <artifact alias>
      source: <build pipeline name>
      trigger: true    # enable CD trigger

variables:
  <key>: <value>       # from top-level pipeline variables

stages:
  - stage: <sanitized environment name>
    displayName: <original environment name>
    ...
```

#### Stages (from `environments[]`)

Each `environment` becomes a `stage`. Preserve the original display name; sanitize the stage
identifier (replace spaces/special chars with underscores, ensure it starts with a letter).

```yaml
- stage: Deploy_Staging
  displayName: Deploy to Staging
  dependsOn: []        # infer from environment rank/conditions; empty = no dependency
  condition: succeeded()
  variables:
    <env-scoped variables>
  jobs:
    - deployment: ...  # preferred for deployment stages
```

**Approval gates** → Use `environment:` with approval checks in Azure DevOps Environments, or emit
a comment block explaining that pre/post approvals must be configured as Environment Checks in the
YAML pipeline UI. Do not silently drop approvals — always emit a `# APPROVAL REQUIRED` comment.

#### Jobs (from `deployPhases[]`)

| Classic deployPhase type | YAML equivalent |
|---|---|
| `agentBasedDeployment` | `job:` or `deployment:` |
| `runOnServer` (agentless) | `job: { pool: server }` |
| `machineGroupBasedDeployment` | `deployment:` with `environment: <name>` and deployment group pool |

For deployment jobs (most common), prefer the `deployment:` job type with a `deploy` strategy:

```yaml
jobs:
  - deployment: Deploy
    displayName: Deploy to environment
    pool:
      name: <agent pool name>
    environment: <environment name>
    strategy:
      runOnce:
        deploy:
          steps:
            - <tasks>
```

#### Tasks (from `workflowTasks[]`)

Each task has a `taskId` (GUID), `name`, `version`, and `inputs` dictionary. Map these to YAML task
references:

```yaml
- task: <TaskName>@<majorVersion>
  displayName: <task display name>
  inputs:
    <key>: <value>
  condition: <condition expression>    # if task.condition is set
  continueOnError: <bool>
  enabled: <bool>
  timeoutInMinutes: <int>
```

For **well-known task GUIDs**, use the human-readable name (see `references/task_guid_map.md`).
For unknown GUIDs, emit the GUID with a `# TODO: verify task name` comment.

#### Variables

- Pipeline-level variables → top-level `variables:` block
- Stage-level variables → `variables:` under the `stage:`
- Secret variables → emit as `${{ variables['<name>'] }}` with a comment that secrets must be
  linked to a Variable Group or marked secret in the Library.
- Variable Groups → emit as:
  ```yaml
  variables:
    - group: <variableGroupName>
  ```

#### Conditions and triggers

- Environment rank/order → `dependsOn:` with `condition: succeeded()`
- "Run after any previous stage, even on failure" → `condition: always()`
- Artifact triggers with branch filters → `resources.pipelines[].trigger.branches`

---

### Step 4 — Run the conversion script

The bundled script does the heavy mechanical lifting:

```bash
python scripts/convert_pipeline.py <input.json> --out <output.yaml>
```

This produces a well-structured YAML file. After running it:
1. Read the generated YAML.
2. Check for `# TODO` comments that need human attention.
3. Summarize every `# TODO` and `# APPROVAL REQUIRED` comment for the user.
4. Highlight any tasks with unknown GUIDs.

---

### Step 5 — Produce the final output

Present the YAML to the user with:
1. **The complete YAML file** — ready to commit as `azure-pipelines.yml` or
   `pipelines/<name>.yml`.
2. **Migration notes** — a concise summary of:
   - Approvals / gates that need to be configured as Environment Checks
   - Variable groups that need to be linked
   - Any unknown task GUIDs
   - Agent pool names that may need updating
   - Any features not fully representable in YAML (e.g., deployment groups, some gate types)
3. **Next steps** — brief guidance on committing the file and pointing the Azure Pipeline at it.

---

## Output format

Always save the YAML as an artifact. Use this header comment in the generated file:

```yaml
# Generated by azure-pipeline-converter skill
# Source: <original pipeline name>
# Converted: <date>
# Review all '# TODO' comments before committing.
```

Structure the YAML with logical groupings and inline comments explaining non-obvious mappings.
Aim for clarity over compactness — this file will be read and maintained by humans.

---

## Edge cases and special handling

- **Multiple artifacts**: create multiple `resources.pipelines` entries; if one is a Git repo
  artifact, use `resources.repositories` instead.
- **Parallel jobs**: when a deploy phase has `parallelExecution.parallelExecutionType = multiMachine`
  or `multiConfiguration`, emit a matrix strategy.
- **Rollback phases**: emit as a separate job with `condition: failed()`.
- **Scheduled triggers**: convert release schedule triggers to YAML `schedules:` block.
- **Empty/disabled tasks**: skip disabled tasks but add a comment `# <task name> — disabled`.
- **Cloned/forked environments**: treat each as its own stage; note in comments if they share
  variable groups.
- **Large pipelines (>10 stages)**: still convert all stages; consider splitting into template files
  and emit a note suggesting `extends:` templates for maintainability.

---

## Reference files

- `references/task_guid_map.md` — Maps well-known Azure DevOps task GUIDs to task names
- `references/yaml_schema_guide.md` — Quick reference for Azure Pipelines YAML schema

Read these files when you need to look up a specific task GUID or verify YAML syntax.
