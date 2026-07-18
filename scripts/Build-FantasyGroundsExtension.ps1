[CmdletBinding()]
param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repositoryRoot 'integrations\fantasy_grounds\extension\LecternSync'
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repositoryRoot 'dist\fantasy-grounds'
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
$extensionPath = Join-Path $outputRoot 'LecternSync.ext'

if (-not (Test-Path -LiteralPath (Join-Path $source 'extension.xml') -PathType Leaf)) {
    throw "Fantasy Grounds extension source is incomplete: $source"
}

New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
if (Test-Path -LiteralPath $extensionPath) { Remove-Item -LiteralPath $extensionPath -Force }

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($extensionPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $sourcePrefix = [System.IO.Path]::GetFullPath($source).TrimEnd('\') + '\'
    foreach ($file in [System.IO.Directory]::EnumerateFiles($source, '*', [System.IO.SearchOption]::AllDirectories)) {
        $entryName = $file.Substring($sourcePrefix.Length).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive,
            $file,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $archive.Dispose()
}
Write-Host "Built Fantasy Grounds extension: $extensionPath"
