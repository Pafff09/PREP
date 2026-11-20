param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$InputDir,

    [Parameter(Mandatory = $true)]
    [string]$NewVideoFps,

    [string]$OutputDir
)

$InputDir = (Resolve-Path -LiteralPath $InputDir).Path

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Iterate through all files in the input directory.
Get-ChildItem -LiteralPath $InputDir -File | ForEach-Object {
    $outputFile = Join-Path $OutputDir "cap_$($_.Name).mp4"
    & $Ffmpeg -i $_.FullName -filter:v "fps=$NewVideoFps" $outputFile
}