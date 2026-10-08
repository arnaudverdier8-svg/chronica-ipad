#!/usr/bin/env bash
# Rebuild KEYFRAME f1983 (S26, hand-off) for every aspect bucket.
#   CAPTURE=1 ./make_all.sh   also re-captures the live menu (needs the static server, ~6 min per bucket
#                             at 2560x1440 with SwiftShader; deterministic virtual clock, see capture_menu.mjs)
#   ENCODE_TEST=0 ./make_all.sh  skips the 40 s x264/x265 encode-guard experiment
#   ./make_all.sh             rebuilds keyframes, mattes, diffs, reports and the review sheet from the
#                             captures already in ../capture (~1 min per bucket)
set -euo pipefail
HD=/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/handoff
cd "$HD/src"
BUCKETS=("2560 1440 16x9 c169_a" "2048 1536 4x3 c133_a")
if [[ "${CAPTURE:-0}" == "1" ]]; then
  if ! curl -s -o /dev/null http://127.0.0.1:8765/index.html; then
    nohup python3 -m http.server 8765 --bind 127.0.0.1 --directory /home/user/chronica-ipad > "$HD/work/http.log" 2>&1 &
    sleep 1
  fi
  for b in "${BUCKETS[@]}"; do
    set -- $b
    # menu frame 30 = 0.5 s of game time after callMain: nameplates have settled (frames 1-~20 pop in),
    # the camera still holds its first focus (the tour pans only after 3 s = 180 frames)
    CW=$1 CH=$2; OUTD="$HD/capture/$4"
    W=$CW H=$CH OUT="$OUTD" FRAMES=${FRAMES:-30} nice -n 5 /opt/node22/bin/node capture_menu.mjs
  done
fi
for b in "${BUCKETS[@]}"; do
  set -- $b
  nice -n 5 python3 handoff.py "$HD/capture/$4/menu_${1}x${2}_mf030_r0.png" "$HD" "${3}_${1}x${2}" > /dev/null
  echo "built f1983_${3}_${1}x${2}.png"
done
# v2 polish: card frame/field/contents mattes, content geometry, parchment target, G12 mask (needs the mattes above)
nice -n 5 python3 polish.py "$HD" > /dev/null
nice -n 5 python3 dissolve_sim.py "$HD" > /dev/null
[[ "${ENCODE_TEST:-1}" == "1" ]] && nice -n 5 python3 encode_guard_test.py "$HD" > /dev/null
nice -n 5 python3 write_spec.py "$HD"
nice -n 5 python3 qa_images.py "$HD" > /dev/null
nice -n 5 python3 review_sheet.py "$HD"
echo "review sheet: $HD/review_sheet_f1983.png"
# tag every deliverable PNG as sRGB (no pixel changes; captures are left as written by the browser)
TAGS=("$HD/review_sheet_f1983.png" "$HD/mattes_16x9_2560x1440" "$HD/mattes_4x3_2048x1536")
for b in "${BUCKETS[@]}"; do set -- $b; TAGS+=("$HD/f1983_${3}_${1}x${2}.png" "$HD/verify_diff_${3}_${1}x${2}.png"); done
python3 png_srgb.py "${TAGS[@]}"      # the *_v1 files are never touched
# independent checks: outside-card diff vs the live capture (must be 0), candle flame/unlit recomposition (<= 1/255)
python3 verify_outside_card.py "$HD" --ref-suffix _v1
for d in mattes_16x9_2560x1440 mattes_4x3_2048x1536; do python3 verify_flames.py "$HD/$d" 1.0 | grep -E 'candle|table|max_|px_over' | tr -d '\n '; echo; done
