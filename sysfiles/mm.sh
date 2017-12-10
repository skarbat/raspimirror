#!/bin/bash
#
# Script to start MagicMirror automatically through PM2
#

cd ~/MagicMirror
DISPLAY=:0 npm start
