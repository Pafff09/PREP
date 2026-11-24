#!/bin/bash

### Load ffmpeg ###
ffmpeg=$1

### ARGS ###
INPUT=$2
NAME=$3
OUTPUT_DIR=$4
BRIGHTNESS=$5
CONTRAST=$6

### Go to the output directory
cd $OUTPUT_DIR

### Change brightness and contrast
$ffmpeg -y -i $INPUT -vf "eq=brightness=$BRIGHTNESS:contrast=$CONTRAST" $NAME.mp4