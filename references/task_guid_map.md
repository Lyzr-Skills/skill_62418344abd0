# Azure DevOps Task GUID → Name Map

This reference maps the most common Azure DevOps built-in task GUIDs to their human-readable YAML
task names. Use this when the JSON contains a `taskId` field that is a GUID.

The `convert_pipeline.py` script already includes these internally; this file is for manual
verification and reference when you encounter a GUID not yet in the script.

## Format
`GUID` → `TaskName@MajorVersion`

---

## Build & Compile

| GUID | YAML Task |
|------|-----------|
| `9c3e8943-130d-4c78-ac63-8af81df62dfb` | `VSBuild@1` |
| `7b5a6198-930e-4bc5-80f9-cb60bfea1e1a` | `DotNetCoreCLI@2` |
| `ac4ee482-65da-4485-a532-7b085873ddba` | `Maven@3` |
| `0675668a-7bba-4ccb-901d-5ad6554ca653` | `Gradle@2` |

## Script Execution

| GUID | YAML Task |
|------|-----------|
| `e213ff0f-5d5c-4791-802d-52ea3e7be1f1` | `PowerShell@2` |
| `71a9a2d3-a98a-4caa-96ab-affca411ecda` | `PowerShell@2` (inline) |
| `d9bafed4-0b18-4f58-968d-86655b4d2ce9` | `CmdLine@2` |
| `de9ce4e3-d547-43cc-b7df-b8571f54b9fb` | `Bash@3` |
| `2ca8fe15-42ea-4b26-80f1-e0738ec17e89` | `AzureCLI@2` |
| `1e244d32-2dd4-4165-96fb-b7441ca9331e` | `AzurePowerShell@5` |

## File Operations

| GUID | YAML Task |
|------|-----------|
| `6c731c3c-3c68-459a-a5c9-bde6e6595b5b` | `CopyFiles@2` |
| `2a6f5f40-0d36-4ff7-9edd-6b6d77b4cf23` | `DeleteFiles@1` |
| `5bfb729a-a7c8-4a78-a7c3-20002a0a4c3a` | `ExtractFiles@1` |
| `8c3741e7-4fd9-4e26-9a2a-b9e0b2f9c83b` | `ArchiveFiles@2` |
| `6f8c69a5-b023-428e-a125-fccf4d230905` | `FtpUpload@2` |

## Artifacts

| GUID | YAML Task |
|------|-----------|
| `7c6a6b71-4355-4e1b-ab14-44b07e4b7a6f` | `PublishBuildArtifacts@1` |
| `a8515ec8-7254-4ffd-912c-86772e2b5962` | `DownloadBuildArtifacts@0` |

## Package Management

| GUID | YAML Task |
|------|-----------|
| `61f2a582-95ae-4948-b34d-a1b3c4f6a737` | `NuGetToolInstaller@0` |
| `333b11bd-d341-40d9-afcf-b32d5ce6f23b` | `NuGetCommand@2` |
| `fe47e961-9fa8-4106-8639-368c022d43ad` | `Npm@1` |

## Azure Deployments

| GUID | YAML Task |
|------|-----------|
| `497d490f-eea7-4f2b-ab94-48d9c1acdcb1` | `AzureRmWebAppDeployment@4` |
| `2e536346-de1a-469e-aea2-b8d000853a61` | `AzureFunctionApp@1` |
| `4dda660c-b643-4598-a4a2-61080d0002d9` | `AzureAppServiceSettings@1` |
| `94a74903-f93f-4075-884f-dc11f34058b4` | `AzureKeyVault@2` |
| `b7b1f1c9-ee60-44ea-b7e6-1f77bfc2c6e2` | `SqlAzureDacpacDeployment@1` |
| `3ab11522-a7b4-47bc-8f22-6d2a1e3d9e1f` | `AzureResourceManagerTemplateDeployment@3` |

## Containers & Kubernetes

| GUID | YAML Task |
|------|-----------|
| `3b4e0e33-d79f-4e97-b7b5-ef1c19a7d5ad` | `Docker@2` |
| `8d2c8a62-c4d0-49a3-8c3e-0a0b7a3a8b3a` | `KubernetesManifest@0` |

## Testing

| GUID | YAML Task |
|------|-----------|
| `0b0f01ed-7dde-43ff-9cbb-e48954daf9b1` | `VSTest@2` |
| `c1e1d6ae-5a7d-4f87-ab91-4a7c62c16d3b` | `PublishTestResults@2` |

## Infrastructure

| GUID | YAML Task |
|------|-----------|
| `c6f85bf2-0e0d-4073-a84c-1f5b1a0b2e4d` | `TerraformInstaller@0` |
| `5e09a40c-5c18-4e2b-a1d1-7f28e0a5e1b9` | `TerraformTaskV4@4` |
| `9a4e4fce-c99b-4b5a-9ae2-ea00ce6db2ef` | `ServiceFabricDeploy@1` |

---

## Finding unknown GUIDs

If you encounter a GUID not listed above:

1. Search the [azure-pipelines-tasks GitHub repo](https://github.com/microsoft/azure-pipelines-tasks)
   for the GUID in `task.json` files.
2. Or search Azure DevOps docs: `https://docs.microsoft.com/azure/devops/pipelines/tasks/`
3. Emit a `# TODO: verify task name/version (GUID: <guid>)` comment in the YAML output.
