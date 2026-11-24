#!/bin/bash

### Load ffmpeg from path ###
ffmpeg=$1

### Parameters ###
INPUT_DIR=$2
OUTPUT_DIR=$3
WIDTH=$4
HEIGHT=$5

### LOOP all Files from INPUT_DIR ###
cd $INPUT_DIR
for file in *
do  
    # Resize the video to the desired WIDTH x HEIGHT
    # Add the padding
    $ffmpeg -y -i $file\
            -vf "scale=(iw*sar)*min($WIDTH/(iw*sar)\,$HEIGHT/ih):ih*min($WIDTH/(iw*sar)\,$HEIGHT/ih),\
            pad=$WIDTH:$HEIGHT:($WIDTH-iw*min($WIDTH/iw\,$HEIGHT/ih))/2:($HEIGHT-ih*min($WIDTH/iw\,$HEIGHT/ih))/2"\
            $OUTPUT_DIR/$file
done