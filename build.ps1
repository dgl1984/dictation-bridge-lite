# Copyright (C) 2026 Derek Lane and DictationBridge Lite contributors
# SPDX-License-Identifier: GPL-2.0-only

param(
	[switch]$SkipNative
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$NativeSource = Join-Path $ProjectRoot "native"
$AddonSource = Join-Path $ProjectRoot "addon"
$BuildRoot = Join-Path $ProjectRoot "build"
$StageRoot = Join-Path $BuildRoot "addon-stage"
$OutputRoot = Join-Path $ProjectRoot "output"
$ManifestPath = Join-Path $AddonSource "manifest.ini"
$ManifestText = Get-Content -LiteralPath $ManifestPath -Raw
$VersionMatch = [regex]::Match($ManifestText, '(?m)^version\s*=\s*"([^"]+)"\s*$')
if (-not $VersionMatch.Success) { throw "Unable to read the add-on version from manifest.ini." }
$AddonVersion = $VersionMatch.Groups[1].Value
$OutputAddon = Join-Path $OutputRoot "DictationBridgeLite-$AddonVersion.nvda-addon"

function Reset-Directory([string]$Path) {
	if (Test-Path $Path) {
		Remove-Item -LiteralPath $Path -Recurse -Force
	}
	New-Item -ItemType Directory -Path $Path | Out-Null
}

function Build-NativeArchitecture([string]$Name, [string]$Platform) {
	$BuildDirectory = Join-Path $BuildRoot "native-$Name"
	Write-Host "Configuring native $Name components..."
	& cmake -S $NativeSource -B $BuildDirectory -A $Platform
	if ($LASTEXITCODE -ne 0) { throw "CMake configuration failed for $Name." }
	Write-Host "Building native $Name components..."
	& cmake --build $BuildDirectory --config Release --parallel
	if ($LASTEXITCODE -ne 0) { throw "Native build failed for $Name." }
	return (Join-Path $BuildDirectory "bin")
}

New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
Reset-Directory $StageRoot
Reset-Directory $OutputRoot
Copy-Item -Path (Join-Path $AddonSource "*") -Destination $StageRoot -Recurse -Force

if (-not $SkipNative) {
	if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
		throw "CMake was not found. Install the Desktop development with C++ workload for Visual Studio 2022, including CMake tools."
	}
	$Win32Bin = Build-NativeArchitecture "win32" "Win32"
	$X64Bin = Build-NativeArchitecture "x64" "x64"
	$NativeFiles = @(
		(Join-Path $Win32Bin "DictationBridgeLiteMaster32.dll"),
		(Join-Path $Win32Bin "DictationBridgeLiteInproc32.dll"),
		(Join-Path $Win32Bin "DictationBridgeLiteLoader32.exe"),
		(Join-Path $X64Bin "DictationBridgeLiteMaster64.dll"),
		(Join-Path $X64Bin "DictationBridgeLiteInproc64.dll"),
		(Join-Path $X64Bin "DictationBridgeLiteLoader64.exe")
	)
	foreach ($File in $NativeFiles) {
		if (-not (Test-Path $File)) { throw "Expected native output is missing: $File" }
		Copy-Item -LiteralPath $File -Destination $StageRoot -Force
	}
} else {
	Write-Host "Packaging Python-only compatibility probe."
	$OutputAddon = Join-Path $OutputRoot "DictationBridgeLite-$AddonVersion-python-probe.nvda-addon"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$TemporaryZip = [System.IO.Path]::ChangeExtension($OutputAddon, ".zip")
if (Test-Path $TemporaryZip) { Remove-Item -LiteralPath $TemporaryZip -Force }
if (Test-Path $OutputAddon) { Remove-Item -LiteralPath $OutputAddon -Force }
[System.IO.Compression.ZipFile]::CreateFromDirectory(
	$StageRoot,
	$TemporaryZip,
	[System.IO.Compression.CompressionLevel]::Optimal,
	$false
)
Move-Item -LiteralPath $TemporaryZip -Destination $OutputAddon
Write-Host "Build complete: $OutputAddon"
