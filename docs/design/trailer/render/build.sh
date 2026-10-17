#!/bin/zsh
# The whole chain:  ./build.sh [name]   ->  out/<name>.mp4  (default name: trailer-v1)
#   1. data/timeline.json from the storyboard, the placed narration, the captions and the checks' code
#   2. every frame of the film, rendered with Playwright through the installed Chrome
#   3. frames + out/mix.wav muxed with ffmpeg (the captions are already burned into the frames)
# Needs out/mix.wav: the mix of narration, music and effects (animatic/tools/mix_eleven.py writes it).
set -e
cd "$(dirname "$0")"
name=${1:-trailer-v1}
python3 build-data.py
rm -rf out/frames
node render.mjs --workers 8
total=$(python3 -c "import json;print(json.load(open('data/timeline.json'))['total'])")
ffmpeg -v error -y -framerate 24 -i out/frames/f%06d.jpg -i out/mix.wav -t "$total" \
  -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 256k -movflags +faststart "out/${name}.mp4"
ls -la "out/${name}.mp4"
