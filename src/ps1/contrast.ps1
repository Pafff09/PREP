param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$In,

    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [string]$Brightness,

    [Parameter(Mandatory = $true)]
    [string]$Contrast
)

$filter = "eq=brightness=$Brightness`:contrast=$Contrast"
$outputFile = Join-Path $OutputDir "$Name.mp4"

& $Ffmpeg -y -i $In -vf $filter $outputFile