#!/bin/bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"/../custom_components

if [ -f ../output/reef_pi.zip ]; then
    rm ../output/reef_pi.zip
fi
mkdir -p ../output
zip -x "*.pyc" -x "reef_pi/__pycache__/" -r ../output/reef_pi.zip reef_pi
