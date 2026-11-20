param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg
)

# Get version to test FFMPEG works
& $Ffmpeg -version