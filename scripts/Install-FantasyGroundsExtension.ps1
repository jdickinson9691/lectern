[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FantasyGroundsDataPath
)

$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repositoryRoot 'integrations\fantasy_grounds\extension\LecternSync'
$dataRoot = [System.IO.Path]::GetFullPath($FantasyGroundsDataPath)
$extensionsRoot = Join-Path $dataRoot 'extensions'
$destination = Join-Path $extensionsRoot 'LecternSync'

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Lectern Sync extension source was not found: $source"
}

if (-not (Test-Path -LiteralPath $dataRoot -PathType Container)) {
    throw "Fantasy Grounds data folder was not found: $dataRoot"
}

$foundExpectedFolder = $false
foreach ($folder in @('campaigns', 'modules', 'rulesets')) {
    if (Test-Path -LiteralPath (Join-Path $dataRoot $folder) -PathType Container) {
        $foundExpectedFolder = $true
        break
    }
}
if (-not $foundExpectedFolder) {
    throw "The selected folder does not look like a Fantasy Grounds data folder: $dataRoot"
}

New-Item -ItemType Directory -Path $extensionsRoot -Force | Out-Null

if (Test-Path -LiteralPath $destination) {
    $resolvedExtensions = [System.IO.Path]::GetFullPath($extensionsRoot).TrimEnd('\')
    $resolvedDestination = [System.IO.Path]::GetFullPath($destination)
    if (-not $resolvedDestination.StartsWith($resolvedExtensions + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to replace a folder outside the selected Fantasy Grounds extensions folder: $resolvedDestination"
    }
    Remove-Item -LiteralPath $destination -Recurse -Force
}

Copy-Item -LiteralPath $source -Destination $destination -Recurse

Write-Host "Installed Lectern Sync development extension to: $destination"
Write-Host 'Restart Fantasy Grounds, select a 5E campaign, and enable Lectern Sync.'
