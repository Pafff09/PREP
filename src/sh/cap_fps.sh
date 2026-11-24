#!/bin/bash

### Load ffmpeg from path###
ffmpeg=$1

### ARGS ###
INPUT=$2
NEW_VIDEO_FPS=$3
OUTPUT_DIR=$4

### If no OUTPUT_DIR is provided, create a new one next to INPUT_DIR
if [ -z "$OUTPUT_DIR" ]; then
    cd "$INPUT"
    OUTPUT_DIR=../fps_capped
    mkdir -p $OUTPUT_DIR
fi

### Iterate through all files in INPUT DIR ###
cd "$INPUT"
for file in *
do
    $ffmpeg -y -i $file -filter:v fps=$NEW_VIDEO_FPS $OUTPUT_DIR/cap_$file.mp4
done
