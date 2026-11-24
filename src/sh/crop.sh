#!/bin/bash

# Parameters
ffmpeg=$1
input=$2
output_dir=$3
filename=$4
x=$5
y=$6
width=$7
height=$8

# Filter
filter="crop=${width}:${height}:${x}:${y}"

# Output file
output_file="${output_dir%/}/${filename}_cropped.mp4"

# FFMPEG - overwrite the existing same name files
$ffmpeg" -y -i "$input" -vf "$filter" "$output_file"