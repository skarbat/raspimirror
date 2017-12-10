#!/bin/bash
#
#  Installs MagicMirror on Raspbian from scratch
#

profile="raspimirror"
logfile="build.log"
htmlfile="build.html"

# Cleanup previous build
if [ -f "$profile.img.gz" ]; then
    rm -fv "$profile.img.gz"
fi

# The echo "n" is an auto response to say No to use pm2 to autostart MM
python -u raspimirror.py "$profile" RENEW > $logfile 2>&1
if [ "$?" == "0" ]; then
    cat $logfile | pygmentize -l console -f html -o $htmlfile
    xsysroot -p "$profile" --release
fi
