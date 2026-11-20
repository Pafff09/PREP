# Parameters
param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$In,

    [Parameter(Mandatory = $true)]
    [int]$X0,

    [Parameter(Mandatory = $true)]
    [int]$Y0,

    [Parameter(Mandatory = $true)]
    [int]$Width,

    [Parameter(Mandatory = $true)]
    [int]$Height,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [string]$Name
)

# Create filter
$filter = "drawbox=x=$X0`:y=$Y0`:w=$Width`:h=$Height`:color=black`:t=fill"

# Create the output file
$outputFile = Join-Path $OutputDir "masked_${Name}.mp4"

# Run FFMPEG
& $Ffmpeg -i $In -vf $filter $outputFile