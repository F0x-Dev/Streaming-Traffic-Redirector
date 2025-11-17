#!/bin/sh
set -e
STREAM_KEY="$1"
if [ -z "$STREAM_KEY" ]; then
  echo "Usage: $0 <stream_key>"
  exit 2
fi
INPUT="rtmp://nginx-rtmp/live/${STREAM_KEY}"
OUTDIR="/var/www/hls/${STREAM_KEY}"
mkdir -p "${OUTDIR}"
rm -rf "${OUTDIR}"/*
mkdir -p "${OUTDIR}/360p" "${OUTDIR}/720p" "${OUTDIR}/1080p"
ffmpeg -hide_banner -y -i "${INPUT}"   -map 0:v -map 0:a -c:a aac -ar 44100 -b:a 128k   -filter_complex "[0:v]split=3[v360][v720][v1080];[v360]scale=w=640:h=360:force_original_aspect_ratio=decrease[v360out];[v720]scale=w=1280:h=720:force_original_aspect_ratio=decrease[v720out];[v1080]scale=w=1920:h=1080:force_original_aspect_ratio=decrease[v1080out]"   -map "[v360out]" -c:v libx264 -profile:v baseline -preset veryfast -b:v:0 800k -maxrate:0 856k -bufsize:0 1200k -g 48 -sc_threshold 0 -hls_time 4 -hls_playlist_type event -hls_segment_filename "${OUTDIR}/360p/seg_%03d.ts" "${OUTDIR}/360p/playlist.m3u8"   -map "[v720out]" -c:v libx264 -profile:v main -preset veryfast -b:v:1 2500k -maxrate:1 2675k -bufsize:1 4200k -g 48 -sc_threshold 0 -hls_time 4 -hls_playlist_type event -hls_segment_filename "${OUTDIR}/720p/seg_%03d.ts" "${OUTDIR}/720p/playlist.m3u8"   -map "[v1080out]" -c:v libx264 -profile:v high -preset veryfast -b:v:2 5000k -maxrate:2 5350k -bufsize:2 7500k -g 48 -sc_threshold 0 -hls_time 4 -hls_playlist_type event -hls_segment_filename "${OUTDIR}/1080p/seg_%03d.ts" "${OUTDIR}/1080p/playlist.m3u8"
cat > "${OUTDIR}/playlist.m3u8" <<EOF
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360
360p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2700000,RESOLUTION=1280x720
720p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=5500000,RESOLUTION=1920x1080
1080p/playlist.m3u8
EOF
