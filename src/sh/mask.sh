#!/bin/bash

### Load ffmpeg ###
ffmpeg=$1

### ARGS ###
INPUT=$2
X0=$3
Y0=$4
WIDTH=$5
HEIGHT=$6
OUTPUT_DIR=$7
NAME=$8

$ffmpeg -y -i $INPUT -vf "drawbox=x=$X0:y=$Y0:w=$WIDTH:h=$HEIGHT:color=black:t=fill" "${OUTPUT_DIR}/masked_${NAME}.mp4"