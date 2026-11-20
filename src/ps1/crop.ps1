param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg,

    [Parameter(Mandatory = $true)]
    [string]$In,

    [Parameter(Mandatory = $true)]
    [string]$Coords,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [Parameter(Mandatory = $true)]
    [string]$Names
)

$coordList = $Coords -split '/'
$nameList = $Names -split '/'

for ($i = 0; $i -lt $coordList.Count; $i++) {
    # Remove the first and last character, then split on commas or spaces.
    $coord = $coordList[$i].Substring(1, $coordList[$i].Length - 2)
    $values = $coord -split '[,\s]+'

    $filter = "crop=$($values[2]):$($values[3]):$($values[0]):$($values[1])"
    $outputFile = Join-Path $OutputDir "$($nameList[$i])_croped.mp4"

    & $Ffmpeg -i $In -filter:v $filter $outputFile
}