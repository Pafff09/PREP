# Input parameters in order
param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$InputDir,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [int]$Width,

    [Parameter(Mandatory = $true)]
    [int]$Height
)

# Filter that will be applied
$filter = "scale=(iw*sar)*min($Width/(iw*sar)\,$Height/ih):ih*min($Width/(iw*sar)\,$Height/ih),pad=$Width`:$Height`:($Width-iw*min($Width/iw\,$Height/ih))/2`:($Height-ih*min($Width/iw\,$Height/ih))/2"

# Run FFMPEG
Get-ChildItem -LiteralPath $InputDir -File | ForEach-Object {
    $outputFile = Join-Path $OutputDir $_.Name
    & $Ffmpeg -i $_.FullName -vf $filter $outputFile
}
