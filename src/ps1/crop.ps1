param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$In,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [string]$Filename,

    [Parameter(Mandatory = $true)]
    [int]$X,

    [Parameter(Mandatory = $true)]
    [int]$Y,

    [Parameter(Mandatory = $true)]
    [int]$Width,

    [Parameter(Mandatory = $true)]
    [int]$Height

)

# Create the filter
$filter = "crop=${Width}:${Height}:${X}:${Y}"

# Create the output path
$outputFile = Join-Path $OutputDir "${Filename}_cropped.mp4"

# Will overwrite the file, if the same name is present
& $Ffmpeg -y -i $In -vf $filter $outputFile