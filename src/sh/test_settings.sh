#!/bin/bash

### Load the provided ffmpeg bin path ###
Ffmpeg_bin_path=$1

### Get version ###
$Ffmpeg_bin_path\ffmpeg.exe -version