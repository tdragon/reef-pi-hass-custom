#!/bin/bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"/..

if [ -f ./output/reef_pi.zip ]; then
    rm ./output/reef_pi.zip
fi
mkdir -p ./output
cd custom_components/reef_pi/
zip -x "*.pyc" -x "reef_pi/__pycache__/" -r ../../output/reef_pi.zip ./
