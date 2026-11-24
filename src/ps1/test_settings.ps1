param(
    [Parameter(Mandatory = $true)]
    [string]$Ffmpeg_bin_path
)

# Get version to test FFMPEG works
& $Ffmpeg_bin_path\ffmpeg.exe -version