#!/bin/sh

EXPORTPY="[PATH_TO_EXPORT.PY]"
CONVERTSH="[PATH_TO_CONVERT.SH]"
ROOT_DIR=$(pwd)
YEAR=$1
CONTENT_PATH="[HUGO_BASE_DIR]/content/photo/"
OUTPUT_PATH="[HUGO_BASE_DIR]/image_store/"
GALLERYURL="/photos"

trap 'echo "exiting..."; exit;' INT

for ALBUM in $(find ${ROOT_DIR}/${YEAR} -maxdepth 1 -mindepth 1  -type d | sort);
do
  TMPLOG=$(tempfile)
  echo Exporting ${ALBUM} templog: ${TMPLOG}
  python3 ${EXPORTPY} -i ${ALBUM} -o ${OUTPUT_PATH}/${YEAR}/ -c ${CONTENT_PATH}/${YEAR}/ -g ${GALLERYURL}/${YEAR} -l ${TMPLOG}
  # Comment the following line if you only need the content files 
  # without converting photos again
  sh ${CONVERTSH} ${TMPLOG}
  rm ${TMPLOG}
done;
