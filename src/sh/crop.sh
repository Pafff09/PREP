#!/bin/bash

### Load ffmpeg ###
ffmpeg=$1

### ARGS ###
INPUT=$2
COORDS=$3
OUTPUT_DIR=$4
NAMES=$5

# Go to output directory to facilitate pathing for saving
cd "$OUTPUT_DIR"

# Parse the Coordinates & Names
IFS='/' read -a array_coords <<< "$COORDS"
IFS='/' read -a array_names <<< "$NAMES"

declare -i i=0
for coords in "${array_coords[@]}"; do 
    ((i=i+1))

    coord=${coords:1:-1}
    IFS=', ' read -a array2 <<< "$coord"

    $ffmpeg -i $INPUT -filter:v crop=${array2[2]}:${array2[3]}:${array2[0]}:${array2[1]} ${array_names[i-1]}_croped.mp4

done