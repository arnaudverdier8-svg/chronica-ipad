#!/bin/sh
# encode frames f1664-1782 + the matching audio slice (samples 1664*1470 .. 1783*1470 of the padded 44.1 kHz master)
# usage: encode.sh FRAMEDIR OUT.mp4 [crf]
P=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa
CRF=${3:-14}
ffmpeg -y -loglevel error -framerate 30 -start_number 1664 -i "$1/f%04d.png" \
  -i $P/audio/audio_master_1984f_s16.wav \
  -filter_complex "[1:a]atrim=start_sample=2446080:end_sample=2621010,asetpts=PTS-STARTPTS[a];[0:v]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]" \
  -map "[v]" -map "[a]" -frames:v 119 \
  -c:v libx264 -preset slow -crf $CRF -profile:v high -pix_fmt yuv420p -x264-params aq-mode=3:aq-strength=1.1:deblock=-1,-1 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 44100 -movflags +faststart "$2"
