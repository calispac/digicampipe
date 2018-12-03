#!/usr/bin/env bash

pixels=$(echo ${DIGICAM_PIXELS[@]} | tr -s ' ' ',')

digicam-raw --compute --output=$GHV_ON_RAW_HISTO --pixel=$pixels ${DIGICAM_GHV_ON_FILES[@]}
digicam-rate-scan --compute --output=$GHV_ON_RATE_SCAN --threshold_step=1 ${DIGICAM_GHV_ON_FILES[@]}

# digicam-raw --save_figures --output=$GHV_ON_RAW_HISTO --pixel=$pixels ${DIGICAM_GHV_ON_FILES[@]}
