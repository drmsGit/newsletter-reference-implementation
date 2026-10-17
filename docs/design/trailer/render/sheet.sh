#!/bin/zsh
# Contact sheet of the preview frames:  ./sheet.sh [columns]   ->  out/sheet.jpg
cols=${1:-2}
n=$(ls out/preview/t*.jpg | wc -l | tr -d ' ')
rows=$(( (n + cols - 1) / cols ))
w=$(( 1920 / cols ))
[ $cols -gt 2 ] && w=$(( 1600 / cols ))
ffmpeg -v error -y -pattern_type glob -i 'out/preview/t*.jpg' -vf "scale=${w}:-1,tile=${cols}x${rows}:padding=6:color=0x888888" -frames:v 1 -update 1 out/sheet.jpg
echo out/sheet.jpg
