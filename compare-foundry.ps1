<#
.SYNOPSIS
  Compare two Foundry projects (network, identity, auth, deployments, RBAC) and print only the differences.

.EXAMPLE
  ./compare-foundry.ps1 `
    -WorkingProjectId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<acct>/projects/<proj>" `
    -FailingProjectId "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<acct>/projects/<proj>"

  Project resource IDs: Foundry portal -> project -> Overview, or Azure portal -> project -> Properties -> Resource ID.
  Requires: az login (Reader on both accounts is enough).
#>
param(
    [Parameter(Mandatory)] [string] $WorkingProjectId,
    [Parameter(Mandatory)] [string] $FailingProjectId,
    [string] $OutDir = "."
)

$ErrorActionPreference = "Stop"

# Keys that always differ between two resources and are not interesting.
$ignore = '(^|\.)(id|name|etag|principalId|tenantId|clientId|endpoint|endpoints|internalId|customSubDomainName|resourceGroup|createdAt|lastModifiedAt|createdBy|lastModifiedBy|systemData|resourceId|privateEndpoint\.id|provisioningState|dateCreated|dateModified|createdByType|lastModifiedByType|subscriptionId|portalUrl|scope|assignmentId|createdOn|updatedOn|description)(\.|=|$)'

function Invoke-AzJson([string[]] $AzArgs) {
    $out = & az @AzArgs -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    return ($out | ConvertFrom-Json)
}

function Convert-ToLines($obj, [string] $prefix = "") {
    if ($null -eq $obj) { "$prefix=<null>"; return }
    if ($obj -is [System.Collections.IEnumerable] -and $obj -isnot [string]) {
        $i = 0
        foreach ($e in $obj) { Convert-ToLines $e "$prefix[$i]"; $i++ }
        if ($i -eq 0) { "$prefix=[]" }
        return
    }
    if ($obj -is [pscustomobject]) {
        foreach ($p in $obj.PSObject.Properties) {
            $key = if ($prefix) { "$prefix.$($p.Name)" } else { $p.Name }
            Convert-ToLines $p.Value $key
        }
        return
    }
    "$prefix=$obj"
}

function Get-Snapshot([string] $ProjectId, [string] $Label) {
    if ($ProjectId -notmatch '^(?<acct>/subscriptions/[^/]+/resourceGroups/[^/]+/providers/Microsoft\.CognitiveServices/accounts/[^/]+)/projects/(?<proj>[^/]+)$') {
        throw "Not a project resource ID: $ProjectId"
    }
    $acctId = $Matches.acct
    $sub = ($acctId -split '/')[2]
    Write-Host "[$Label] reading $acctId" -ForegroundColor Cyan

    $account = Invoke-AzJson @("resource", "show", "--ids", $acctId, "--api-version", "2025-06-01")
    $project = Invoke-AzJson @("resource", "show", "--ids", $ProjectId, "--api-version", "2025-06-01")
    $deployments = Invoke-AzJson @("rest", "--method", "get", "--url", "https://management.azure.com$acctId/deployments?api-version=2025-06-01")
    $privateEndpoints = Invoke-AzJson @("rest", "--method", "get", "--url", "https://management.azure.com$acctId/privateEndpointConnections?api-version=2025-06-01")

    $roles = @()
    $principals = @($project.identity.principalId, $account.identity.principalId) | Where-Object { $_ }
    foreach ($principalId in $principals) {
        $ra = Invoke-AzJson @("role", "assignment", "list", "--assignee", $principalId, "--all", "--subscription", $sub)
        foreach ($r in @($ra)) {
            if ($r.scope -like "$acctId*" -or $acctId -like "$($r.scope)*") {
                $kind = if ($principalId -eq $project.identity.principalId) { "projectMI" } else { "accountMI" }
                $roles += [pscustomobject]@{ identity = $kind; role = $r.roleDefinitionName; scopeLevel = ($r.scope -replace '^.*/providers/', '' -replace '[^/]+$', '<name>') }
            }
        }
    }
    # Who else has access to the account (user-level roles), role names only
    $acctRoles = Invoke-AzJson @("role", "assignment", "list", "--scope", $acctId, "--include-inherited", "--subscription", $sub)

    [pscustomobject]@{
        account           = $account
        project           = $project
        deployments       = @($deployments.value | ForEach-Object {
                [pscustomobject]@{ model = $_.properties.model.name; version = $_.properties.model.version; sku = $_.sku.name; capacity = $_.sku.capacity; state = $_.properties.provisioningState; raiFilter = $_.properties.raiPolicyName } } | Sort-Object model, sku)
        deploymentNames   = @($deployments.value | ForEach-Object { $_.name } | Sort-Object)
        privateEndpoints  = @($privateEndpoints.value | ForEach-Object { $_.properties.privateLinkServiceConnectionState.status })
        managedIdentityRoles = @($roles | Sort-Object identity, role)
        accountRoleCounts = @($acctRoles | Group-Object roleDefinitionName | ForEach-Object { "$($_.Name)=$($_.Count)" } | Sort-Object)
    }
}

$w = Get-Snapshot $WorkingProjectId "working"
$f = Get-Snapshot $FailingProjectId "failing"

$wLines = @(Convert-ToLines $w | Where-Object { $_ -notmatch $ignore } | Sort-Object)
$fLines = @(Convert-ToLines $f | Where-Object { $_ -notmatch $ignore } | Sort-Object)

$wLines | Set-Content (Join-Path $OutDir "working.txt")
$fLines | Set-Content (Join-Path $OutDir "failing.txt")

Write-Host "`n===== DIFFERENCES (<= only in WORKING, => only in FAILING) =====" -ForegroundColor Yellow
$diff = Compare-Object $wLines $fLines
if (-not $diff) { Write-Host "No differences found in the compared settings." }
else { $diff | ForEach-Object { "{0} {1}" -f $_.SideIndicator, $_.InputObject } }
Write-Host "`nFull snapshots written to working.txt and failing.txt in $OutDir"
