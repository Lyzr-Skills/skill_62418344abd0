# Azure Pipelines YAML Schema Quick Reference

Use this guide to verify syntax when building or reviewing the generated YAML.

Full official docs: https://docs.microsoft.com/azure/devops/pipelines/yaml-schema

---

## Top-level structure

```yaml
trigger: none | [ branch-list ] | { branches: { include: [], exclude: [] } }
pr: none | [ branch-list ]

resources:
  pipelines: [...]
  repositories: [...]
  containers: [...]

schedules:
  - cron: '0 2 * * *'
    displayName: Nightly
    branches:
      include: [ main ]
    always: false

variables:
  - name: myVar
    value: myValue
  - group: my-variable-group

stages:
  - stage: ...
```

---

## Stage

```yaml
- stage: StageName           # identifier — letters/numbers/underscores
  displayName: 'Human Name'
  dependsOn: []              # [] = no deps; 'StageName' = depends on one stage
  condition: succeeded()
  variables:
    key: value
  jobs:
    - job: ...
    - deployment: ...
```

### Common conditions

| Expression | Meaning |
|---|---|
| `succeeded()` | Previous stage succeeded |
| `failed()` | Previous stage failed |
| `always()` | Always run regardless |
| `canceled()` | Previous stage was canceled |
| `succeededOrFailed()` | Succeeded or failed (not canceled) |
| `and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))` | Compound |

---

## Job (regular)

```yaml
- job: JobName
  displayName: 'Human Name'
  pool:
    name: 'Agent Pool Name'
    vmImage: ubuntu-latest    # for Microsoft-hosted
  dependsOn: []
  condition: succeeded()
  timeoutInMinutes: 60
  continueOnError: false
  variables:
    key: value
  steps:
    - task: ...
    - script: ...
    - bash: ...
    - pwsh: ...
```

---

## Deployment Job (preferred for release stages)

```yaml
- deployment: DeployName
  displayName: 'Deploy to Production'
  pool:
    name: 'Default'
  environment: my-environment   # creates/references an Environment in Azure DevOps
  strategy:
    runOnce:
      preDeploy:        # optional
        steps: [...]
      deploy:           # main deployment steps
        steps:
          - download: current
          - task: AzureRmWebAppDeployment@4
            inputs: ...
      routeTraffic:     # optional
        steps: [...]
      postRouteTraffic: # optional
        steps: [...]
      on:
        failure:
          steps: [...]
        success:
          steps: [...]
```

### Deployment strategies

| Strategy | Description |
|---|---|
| `runOnce` | Default — deploy once to all targets |
| `rolling` | Gradually replace instances |
| `canary` | Deploy to a % of targets first |

---

## Steps

### Task step

```yaml
- task: TaskName@MajorVersion
  displayName: 'Step description'
  condition: succeeded()
  continueOnError: false
  enabled: true
  timeoutInMinutes: 10
  inputs:
    key: value
  env:
    MY_SECRET: $(secretVar)   # inject secrets as env vars (never in inputs)
```

### Inline script steps

```yaml
- script: echo "hello"          # cmd on Windows, sh on Linux/macOS
- bash: echo "hello"            # always bash
- pwsh: Write-Host "hello"      # always PowerShell Core
- powershell: Write-Host "hello" # Windows PowerShell
```

### Download step (artifacts from resources)

```yaml
- download: current            # downloads all artifacts from current pipeline
- download: pipelineAlias      # downloads from a specific pipeline resource
  artifact: drop
  patterns: '**/*.zip'
```

### Checkout step

```yaml
- checkout: self
- checkout: myRepoAlias
  clean: true
  fetchDepth: 1
```

---

## Variables

```yaml
# Inline
variables:
  key: value
  anotherKey: anotherValue

# Variable groups
variables:
  - group: my-variable-group
  - name: myVar
    value: myValue

# Runtime parameters (replaces release-time variables)
parameters:
  - name: environment
    type: string
    default: staging
    values: [staging, production]
```

### Referencing variables

| Context | Syntax |
|---|---|
| In YAML | `$(variableName)` |
| In conditions | `variables['variableName']` |
| Secrets (never log) | `$(secretVar)` or `${{ variables['secret'] }}` |

---

## Resources

### Pipeline resource (replaces build artifact)

```yaml
resources:
  pipelines:
    - pipeline: myPipeline          # alias used in download steps
      source: 'CI-Build-Pipeline'  # name of the source pipeline
      project: MyProject
      trigger:
        branches:
          include: [ main, release/* ]
```

### Repository resource

```yaml
resources:
  repositories:
    - repository: myRepo
      type: git                   # git (Azure Repos), github, bitbucket
      name: MyProject/MyRepo
      ref: refs/heads/main
```

---

## Approvals and checks (YAML equivalent of classic approvals)

YAML pipelines do not have inline approval syntax. Instead:

1. Create an **Environment** in Azure DevOps (Pipelines → Environments)
2. Add **Approvals** or **Branch control** checks to the Environment
3. Reference the environment in your `deployment:` job

```yaml
- deployment: Deploy
  environment: production   # This environment has approval checks configured
  strategy:
    runOnce:
      deploy:
        steps: [...]
```

---

## Templates (for large pipelines)

Break large pipelines into reusable templates:

```yaml
# azure-pipelines.yml (main file)
stages:
  - template: templates/deploy-stage.yml
    parameters:
      environment: staging
      serviceConnection: sc-staging

# templates/deploy-stage.yml
parameters:
  - name: environment
    type: string
  - name: serviceConnection
    type: string

stages:
  - stage: Deploy_${{ parameters.environment }}
    jobs:
      - deployment: Deploy
        environment: ${{ parameters.environment }}
        ...
```
