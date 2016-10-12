#!/bin/bash

THUMB_SIZE=400
WEB_SIZE=2048
IM_OPTIONS="-strip -quality 95"
WATERMARK_OPTIONS="[PATH_TO_WATERMARK_IMG] -gravity southeast -geometry +30+30 -composite"
ALGO="smallfry"
THUMB_QUALITY="medium"
WEB_QUALITY="high"
JPEGRECOMPRESS="jpeg-recompress"
CONVERT="convert"

TMPDIR=$(mktemp -d)

trap 'echo "exiting..."; exit;' INT

# Convert image to maximum side of 2048px and add water
# Finally recompress it lossy
parallel --colsep ';' -a $1 \
  'START_TIME=$(date +%s.%N);' \
  ${CONVERT} {1} ${IM_OPTIONS} -thumbnail ${WEB_SIZE}x${WEB_SIZE}'\>' ${WATERMARK_OPTIONS} ${TMPDIR}/{1/}";" \
  ${JPEGRECOMPRESS} -Q -s -m ${ALGO} -q ${WEB_QUALITY} ${TMPDIR}/{1/} {2}/${WEB_SIZE}/{3}";" \
  rm ${TMPDIR}/{1/}";" \
  echo [CONVERT WEB '$(echo `date +%s.%N` - $START_TIME | bc -l)' sec] {1/}

# Convert thumbnail to maximum height of 400px
parallel --colsep ';' -a $1 \
  'START_TIME=$(date +%s.%N);' \
  ${CONVERT} {2}/${WEB_SIZE}/{3} ${IM_OPTIONS} -thumbnail 10000x${THUMB_SIZE}'\>' ${TMPDIR}/{3}";" \
  ${JPEGRECOMPRESS} -Q -s -m ${ALGO} -q ${WEB_QUALITY} ${TMPDIR}/{3} {2}/${THUMB_SIZE}/{3}";" \
  rm ${TMPDIR}/{3}";" \
  echo [CONVERT THUMB '$(echo `date +%s.%N` - $START_TIME | bc -l)' sec] {1/} 

rm -Rf ${TMPDIR}