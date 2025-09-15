#!/usr/bin/env bash


echo "🎬️ Making a video of your history."
gource --seconds-per-day 0.1 --time-scale 4 --auto-skip-seconds 1 \
    --key --file-idle-time 0 --max-files 0 --max-file-lag 0.1 \
    --title "Geest Project History" --bloom-multiplier 0.5 --bloom-intensity 0.5 \
    --background 000000 --hide filenames,mouse,progress \
    --output-ppm-stream - |
    ffmpeg -probesize 50M -analyzeduration 100M -y -r 60 -f image2pipe -vcodec ppm -i - \
	-vf scale=1280:-1 -vcodec libx264 -preset fast -pix_fmt yuv420p -crf 1 -threads 0 -bf 0 history.mp4
ffmpeg -i history.mp4 -vf "fps=10,scale=1280:-1:flags=lanczos" -loop 0 history.gif
